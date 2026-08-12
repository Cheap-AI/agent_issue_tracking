"""Check event count in database."""
from backend.core.db import get_session
from sqlalchemy import text

with get_session() as session:
    count = session.execute(text('SELECT COUNT(*) FROM events')).scalar()
    print(f'Total events: {count}')
    
    # Show recent events
    print('\nRecent events:')
    events = session.execute(text('''
        SELECT e.issue_id, i.title, e.title as event_title, e.event_date 
        FROM events e
        JOIN issues i ON e.issue_id = i.id
        ORDER BY e.created_at DESC 
        LIMIT 10
    ''')).fetchall()
    
    for event in events:
        date_str = str(event[3]) if event[3] else 'No date'
        print(f'  {event[0]}: {event[2]} ({date_str})')
        print(f'    Issue: {event[1][:60]}...')
