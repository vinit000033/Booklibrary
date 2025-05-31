#!/usr/bin/env python3
"""
IPM Library Telegram Bot - Utility Functions
"""

import json
import os
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import uuid
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

def load_storage() -> Dict:
    """Load data from storage.json file"""
    try:
        if not os.path.exists('storage.json'):
            return {"users": [], "books": []}
        
        with open('storage.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading storage: {e}")
        return {"users": [], "books": []}

def save_storage(data: Dict) -> bool:
    """Save data to storage.json file"""
    try:
        with open('storage.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving storage: {e}")
        return False

def add_user(user_id: int, username: str, first_name: str) -> bool:
    """Add or update user in storage"""
    try:
        storage = load_storage()
        
        # Check if user already exists
        for user in storage['users']:
            if user['id'] == user_id:
                # Update existing user info
                user['username'] = username
                user['first_name'] = first_name
                user['last_seen'] = datetime.now().isoformat()
                save_storage(storage)
                return True
        
        # Add new user
        new_user = {
            'id': user_id,
            'username': username,
            'first_name': first_name,
            'joined_date': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat()
        }
        
        storage['users'].append(new_user)
        save_storage(storage)
        logger.info(f"Added new user: {username} ({user_id})")
        return True
        
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return False

def validate_google_drive_link(link: str) -> str:
    """Validate and convert Google Drive link to proper sharing format"""
    if not link or 'drive.google.com' not in link:
        return link
    
    # Extract file ID from various Google Drive URL formats
    file_id_patterns = [
        r'/file/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
        r'/d/([a-zA-Z0-9-_]+)',
    ]
    
    for pattern in file_id_patterns:
        match = re.search(pattern, link)
        if match:
            file_id = match.group(1)
            # Convert to direct sharing link
            sharing_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
            logger.info(f"Converted Google Drive link: {link} -> {sharing_link}")
            return sharing_link
    
    # If no pattern matches, return original link
    return link

def add_book_submission(title: str, author: str, submitter_id: int, 
                       submitter_username: str, submitter_name: str,
                       gdrive_link: str = "", file_id: str = "") -> str:
    """Add a new book submission to storage"""
    try:
        storage = load_storage()
        
        # Generate unique ID for the book
        book_id = str(uuid.uuid4())
        
        # Validate and fix Google Drive link
        validated_link = validate_google_drive_link(gdrive_link) if gdrive_link else ""
        
        new_book = {
            'id': book_id,
            'title': title,
            'author': author,
            'submitter_id': submitter_id,
            'submitter_username': submitter_username,
            'submitter_name': submitter_name,
            'gdrive_link': validated_link,
            'file_id': file_id,
            'timestamp': datetime.now().isoformat(),
            'approved': False,
            'approved_date': None,
            'approved_by': None
        }
        
        storage['books'].append(new_book)
        save_storage(storage)
        logger.info(f"Added book submission: {title} by {author}")
        return book_id
        
    except Exception as e:
        logger.error(f"Error adding book submission: {e}")
        return ""

def get_pending_books() -> List[Dict]:
    """Get all pending (unapproved) book submissions"""
    try:
        storage = load_storage()
        pending = [book for book in storage['books'] if not book['approved']]
        return pending
    except Exception as e:
        logger.error(f"Error getting pending books: {e}")
        return []

def approve_book(book_id: str, approved_by: str = "") -> Tuple[bool, Optional[Dict]]:
    """Approve a book submission"""
    try:
        storage = load_storage()
        
        for book in storage['books']:
            if book['id'] == book_id:
                book['approved'] = True
                book['approved_date'] = datetime.now().isoformat()
                book['approved_by'] = approved_by
                save_storage(storage)
                logger.info(f"Approved book: {book['title']}")
                return True, book
        
        logger.warning(f"Book not found for approval: {book_id}")
        return False, None
        
    except Exception as e:
        logger.error(f"Error approving book: {e}")
        return False, None

def get_weekly_leaderboard() -> List[Tuple[Dict, int]]:
    """Get weekly leaderboard of top contributors"""
    return get_leaderboard_by_period(7)

def get_monthly_leaderboard() -> List[Tuple[Dict, int]]:
    """Get monthly leaderboard of top contributors"""
    return get_leaderboard_by_period(30)

def get_alltime_leaderboard() -> List[Tuple[Dict, int]]:
    """Get all-time leaderboard of top contributors"""
    return get_leaderboard_by_period(None)

def get_leaderboard_by_period(days: Optional[int]) -> List[Tuple[Dict, int]]:
    """Get leaderboard for a specific time period"""
    try:
        storage = load_storage()
        
        # Filter books by time period
        filtered_books = []
        if days is None:
            # All time - get all approved books
            filtered_books = [book for book in storage['books'] if book['approved']]
        else:
            # Specific period
            cutoff_date = datetime.now() - timedelta(days=days)
            for book in storage['books']:
                if book['approved'] and book.get('approved_date'):
                    try:
                        approved_date = datetime.fromisoformat(book['approved_date'])
                        if approved_date >= cutoff_date:
                            filtered_books.append(book)
                    except:
                        continue
        
        # Count contributions by user
        user_contributions = {}
        for book in filtered_books:
            user_id = book['submitter_id']
            if user_id not in user_contributions:
                user_contributions[user_id] = {
                    'count': 0,
                    'username': book['submitter_username'],
                    'name': book['submitter_name']
                }
            user_contributions[user_id]['count'] += 1
        
        # Sort by contribution count
        leaderboard = []
        for user_id, data in user_contributions.items():
            user_info = {
                'id': user_id,
                'username': data['username'],
                'name': data['name']
            }
            leaderboard.append((user_info, data['count']))
        
        # Sort by count in descending order
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        
        return leaderboard[:10]  # Return top 10
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return []

def get_all_users() -> List[Dict]:
    """Get all users from storage"""
    try:
        storage = load_storage()
        return storage.get('users', [])
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []

def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in ADMIN_IDS

def get_user_stats(user_id: int) -> Dict:
    """Get statistics for a specific user"""
    try:
        storage = load_storage()
        
        # Count total submissions and approved books
        total_submissions = len([book for book in storage['books'] if book['submitter_id'] == user_id])
        approved_books = len([book for book in storage['books'] if book['submitter_id'] == user_id and book['approved']])
        
        # Get user info
        user_info = None
        for user in storage['users']:
            if user['id'] == user_id:
                user_info = user
                break
        
        return {
            'user_info': user_info,
            'total_submissions': total_submissions,
            'approved_books': approved_books,
            'approval_rate': (approved_books / total_submissions * 100) if total_submissions > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {}

def search_books(query: str) -> List[Dict]:
    """Search for books by title or author"""
    try:
        storage = load_storage()
        query_lower = query.lower()
        
        results = []
        for book in storage['books']:
            if book['approved']:  # Only search approved books
                if (query_lower in book['title'].lower() or 
                    query_lower in book['author'].lower()):
                    results.append(book)
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching books: {e}")
        return []

def get_library_stats() -> Dict:
    """Get overall library statistics"""
    try:
        storage = load_storage()
        
        total_books = len([book for book in storage['books'] if book['approved']])
        total_users = len(storage['users'])
        pending_submissions = len([book for book in storage['books'] if not book['approved']])
        
        # Get most active contributor
        user_contributions = {}
        for book in storage['books']:
            if book['approved']:
                user_id = book['submitter_id']
                user_contributions[user_id] = user_contributions.get(user_id, 0) + 1
        
        most_active_user = None
        if user_contributions:
            most_active_id = max(user_contributions.keys(), key=lambda x: user_contributions[x])
            for user in storage['users']:
                if user['id'] == most_active_id:
                    most_active_user = {
                        'name': user['first_name'],
                        'username': user['username'],
                        'contributions': user_contributions[most_active_id]
                    }
                    break
        
        return {
            'total_books': total_books,
            'total_users': total_users,
            'pending_submissions': pending_submissions,
            'most_active_user': most_active_user
        }
        
    except Exception as e:
        logger.error(f"Error getting library stats: {e}")
        return {}

def backup_storage() -> bool:
    """Create a backup of the storage file"""
    try:
        if os.path.exists('storage.json'):
            backup_filename = f"storage_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open('storage.json', 'r') as src:
                with open(backup_filename, 'w') as dst:
                    dst.write(src.read())
            
            logger.info(f"Storage backup created: {backup_filename}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return False

def clean_old_data(days: int = 90) -> bool:
    """Clean old data from storage (rejected submissions older than specified days)"""
    try:
        storage = load_storage()
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Keep approved books and recent submissions
        cleaned_books = []
        for book in storage['books']:
            book_date = datetime.fromisoformat(book['timestamp'])
            
            # Keep if approved or recent
            if book['approved'] or book_date >= cutoff_date:
                cleaned_books.append(book)
        
        original_count = len(storage['books'])
        storage['books'] = cleaned_books
        save_storage(storage)
        
        cleaned_count = original_count - len(cleaned_books)
        logger.info(f"Cleaned {cleaned_count} old submissions from storage")
        
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning old data: {e}")
        return False
