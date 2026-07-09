import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.generator.synthetic_data import SyntheticDataGenerator, MetricName


@pytest.fixture
def generator():
    """Create a test generator with small dataset."""
    return SyntheticDataGenerator(num_users=5, days_of_data=7)


def test_generator_init(generator):
    """Test generator initialization."""
    assert generator.num_users == 5
    assert generator.days_of_data == 7
    assert generator.start_date is not None
    assert generator.end_date is not None


def test_user_generation(generator):
    """Test user generation."""
    users = generator.generate_users()
    
    assert len(users) == 5
    assert all('name' in user for user in users)
    assert all('age' in user for user in users)
    assert all('gender' in user for user in users)
    assert all('device_type' in user for user in users)
    
    # Age should be reasonable
    assert all(18 <= user['age'] <= 75 for user in users)


def test_heart_rate_generation(generator):
    """Test heart rate event generation."""
    events = generator._generate_heart_rate_events(user_id=1, date=datetime.now())
    
    assert len(events) > 0
    assert all(e['metric_name'] == MetricName.HEART_RATE for e in events)
    assert all(40 <= e['value'] <= 200 for e in events)
    assert all('time' in e for e in events)
    assert all('metadata' in e for e in events)


def test_steps_generation(generator):
    """Test steps event generation."""
    events = generator._generate_steps_events(user_id=1, date=datetime.now())
    
    assert len(events) > 0
    assert all(e['metric_name'] == MetricName.STEPS for e in events)
    assert all(e['value'] >= 0 for e in events)


def test_sleep_generation(generator):
    """Test sleep stage generation."""
    events = generator._generate_sleep_events(user_id=1, date=datetime.now())
    
    assert len(events) > 0
    assert all(e['metric_name'] == MetricName.SLEEP_STAGE for e in events)
    assert all('stage' in e['metadata'] for e in events)


def test_population_generation():
    """Test full population generation."""
    gen = SyntheticDataGenerator(num_users=2, days_of_data=2)
    users, events = gen.generate_population()
    
    assert len(users) == 2
    assert len(events) > 0
    
    # Verify event structure
    for event in events[:10]:  # Check first 10
        assert 'user_id' in event
        assert 'metric_name' in event
        assert 'value' in event
        assert 'time' in event
        assert event['user_id'] in [1, 2]
