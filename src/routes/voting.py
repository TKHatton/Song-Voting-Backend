from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import json
import os
from datetime import datetime
import hashlib

# Optional Google Sheets import
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    print("Google Sheets integration not available - using fallback storage")

voting_bp = Blueprint('voting', __name__)

# Google Sheets configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_google_sheets_client():
    """
    Initialize Google Sheets client using service account credentials.
    Returns None if not available or configured.
    """
    if not GSPREAD_AVAILABLE:
        return None
        
    try:
        credentials_path = os.environ.get('GOOGLE_SHEETS_CREDENTIALS_PATH')
        if not credentials_path or not os.path.exists(credentials_path):
            return None
            
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error initializing Google Sheets client: {e}")
        return None

def get_client_ip():
    """Get client IP address for vote tracking"""
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']

def hash_ip(ip):
    """Hash IP address for privacy"""
    return hashlib.sha256(ip.encode()).hexdigest()

# In-memory storage for demo (in production, use Google Sheets)
votes_storage = {
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0
}

voted_ips = set()

@voting_bp.route('/vote', methods=['POST'])
@cross_origin()
def submit_vote():
    """Submit a vote for a video"""
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        social_follows = data.get('social_follows', {})
        
        if not video_id:
            return jsonify({'error': 'Video ID is required'}), 400
        
        # Check if all social requirements are met
        required_platforms = ['instagram', 'linkedin', 'twitter']
        for platform in required_platforms:
            if not social_follows.get(platform, False):
                return jsonify({'error': f'Must follow on {platform}'}), 400
        
        # Get and hash client IP
        client_ip = get_client_ip()
        ip_hash = hash_ip(client_ip)
        
        # Check if IP has already voted
        if ip_hash in voted_ips:
            return jsonify({'error': 'You have already voted'}), 400
        
        # Record the vote
        if video_id not in votes_storage:
            return jsonify({'error': 'Invalid video ID'}), 400
        
        votes_storage[video_id] += 1
        voted_ips.add(ip_hash)
        
        # In production, save to Google Sheets
        # save_vote_to_sheets(video_id, ip_hash, social_follows)
        
        return jsonify({
            'success': True,
            'message': 'Vote submitted successfully',
            'new_vote_count': votes_storage[video_id]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@voting_bp.route('/votes', methods=['GET'])
@cross_origin()
def get_votes():
    """Get current vote counts for all videos"""
    try:
        return jsonify({
            'success': True,
            'votes': votes_storage,
            'total_votes': sum(votes_storage.values())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@voting_bp.route('/check-voted', methods=['POST'])
@cross_origin()
def check_voted():
    """Check if current IP has already voted"""
    try:
        client_ip = get_client_ip()
        ip_hash = hash_ip(client_ip)
        
        has_voted = ip_hash in voted_ips
        
        return jsonify({
            'success': True,
            'has_voted': has_voted
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@voting_bp.route('/social-verify', methods=['POST'])
@cross_origin()
def verify_social_follows():
    """
    Verify social media follows.
    In production, this would integrate with social media APIs.
    For demo purposes, we'll accept the frontend's verification.
    """
    try:
        data = request.get_json()
        platforms = data.get('platforms', {})
        
        # In production, you would verify with actual social media APIs
        # For demo, we'll return success
        
        return jsonify({
            'success': True,
            'verified_platforms': platforms
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def save_vote_to_sheets(video_id, ip_hash, social_follows):
    """
    Save vote data to Google Sheets.
    This is a placeholder for the actual implementation.
    """
    try:
        # Get Google Sheets client
        client = get_google_sheets_client()
        
        if client is None:
            # Demo mode - log to console
            print(f"Vote recorded: Video {video_id}, IP Hash: {ip_hash[:8]}..., Social: {social_follows}")
            return
        
        # In production implementation:
        # 1. Open the spreadsheet
        # sheet = client.open('SHE IS AI Voting Data').sheet1
        
        # 2. Append the vote data
        # timestamp = datetime.now().isoformat()
        # row = [timestamp, video_id, ip_hash, json.dumps(social_follows)]
        # sheet.append_row(row)
        
    except Exception as e:
        print(f"Error saving to Google Sheets: {e}")

@voting_bp.route('/analytics', methods=['GET'])
@cross_origin()
def get_analytics():
    """Get voting analytics data"""
    try:
        total_votes = sum(votes_storage.values())
        
        # Calculate percentages
        vote_percentages = {}
        for video_id, count in votes_storage.items():
            percentage = (count / total_votes * 100) if total_votes > 0 else 0
            vote_percentages[video_id] = round(percentage, 1)
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_votes': total_votes,
                'vote_counts': votes_storage,
                'vote_percentages': vote_percentages,
                'total_participants': len(voted_ips),
                'videos_count': len(votes_storage)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

