import random
import numpy as np
from datetime import datetime, timedelta
from faker import Faker
from enum import Enum
from typing import List, Dict, Tuple
import json
import logging

logger = logging.getLogger(__name__)

fake = Faker()
random.seed(42)
np.random.seed(42)


class MetricName(str, Enum):
    HEART_RATE = "heart_rate"
    STEPS = "steps"
    SLEEP_DURATION = "sleep_duration"
    SLEEP_STAGE = "sleep_stage"
    BLOOD_OXYGEN = "blood_oxygen"
    WORKOUT_DURATION = "workout_duration"


class SleepStage(str, Enum):
    LIGHT = "light"
    DEEP = "deep"
    REM = "rem"


class SyntheticDataGenerator:
    """Generate realistic health metrics for synthetic users."""
    
    def __init__(self, num_users: int, days_of_data: int):
        self.num_users = num_users
        self.days_of_data = days_of_data
        self.start_date = datetime.now() - timedelta(days=days_of_data)
        self.end_date = datetime.now()
        
        logger.info(f"Initializing generator: {num_users} users, {days_of_data} days")
        logger.info(f"Date range: {self.start_date} to {self.end_date}")
    
    def generate_users(self) -> List[Dict]:
        """Generate synthetic user profiles."""
        users = []
        devices = ["Apple Watch", "Fitbit", "Garmin", "Samsung Galaxy Watch"]
        
        for i in range(self.num_users):
            user = {
                "name": fake.name(),
                "age": random.randint(18, 75),
                "gender": random.choice(["M", "F"]),
                "device_type": random.choice(devices)
            }
            users.append(user)
        
        logger.info(f"Generated {len(users)} synthetic users")
        return users
    
    def _get_base_heart_rate(self, hour: int, is_workout: bool) -> float:
        """Realistic base heart rate depending on time of day."""
        if is_workout:
            return np.random.normal(140, 15)
        
        # Night (10 PM - 6 AM): lower heart rate
        if hour >= 22 or hour < 6:
            return np.random.normal(55, 5)
        
        # Morning (6 AM - 10 AM): ramp up
        if 6 <= hour < 10:
            return np.random.normal(70, 8)
        
        # Day (10 AM - 6 PM): active
        if 10 <= hour < 18:
            return np.random.normal(80, 10)
        
        # Evening (6 PM - 10 PM): calm down
        return np.random.normal(70, 8)
    
    def _generate_heart_rate_events(self, user_id: int, date: datetime) -> List[Dict]:
        """Generate heart rate events (every 5 minutes)."""
        events = []
        hour = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 3% chance of device being off for 12+ hours
        if random.random() < 0.03:
            gap_start = random.randint(0, 11)
            gap_end = gap_start + random.randint(12, 18)
            skip_hours = set(range(gap_start, min(gap_end, 24)))
        else:
            skip_hours = set()
        
        for hour_offset in range(24):
            if hour_offset in skip_hours:
                continue
            
            current_time = hour + timedelta(hours=hour_offset)
            base_hr = self._get_base_heart_rate(hour_offset, False)
            
            # Generate 12 samples per hour (every 5 min)
            for minute in range(0, 60, 5):
                sample_time = current_time.replace(minute=minute)
                
                # Add noise
                value = max(40, min(200, base_hr + np.random.normal(0, 3)))
                
                # 1% outliers (sensor error)
                if random.random() < 0.01:
                    value = random.choice([random.randint(200, 220), random.randint(30, 40)])
                    is_outlier = True
                else:
                    is_outlier = False
                
                events.append({
                    "user_id": user_id,
                    "metric_name": MetricName.HEART_RATE,
                    "value": round(value, 2),
                    "time": sample_time,
                    "metadata": {
                        "is_outlier": is_outlier,
                        "data_quality": "degraded" if is_outlier else "good"
                    }
                })
        
        return events
    
    def _generate_steps_events(self, user_id: int, date: datetime) -> List[Dict]:
        """Generate step count (hourly aggregates)."""
        events = []
        hour = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for hour_offset in range(24):
            current_time = hour + timedelta(hours=hour_offset)
            
            # Activity patterns
            if 0 <= hour_offset < 6:
                # Night: sleeping
                steps = 0
            elif 6 <= hour_offset < 10:
                # Morning: ramping up
                steps = np.random.normal(80, 20)
            elif 10 <= hour_offset < 12:
                # Late morning: active
                steps = np.random.normal(150, 40)
            elif 12 <= hour_offset < 14:
                # Lunch time
                steps = np.random.normal(100, 30)
            elif 14 <= hour_offset < 18:
                # Afternoon: work/exercise
                steps = np.random.normal(180, 50)
            else:
                # Evening: wind down
                steps = np.random.normal(90, 25)
            
            steps = max(0, steps)
            
            # 2% missing data
            if random.random() < 0.02:
                continue
            
            events.append({
                "user_id": user_id,
                "metric_name": MetricName.STEPS,
                "value": round(steps, 0),
                "time": current_time,
                "metadata": {"data_quality": "good"}
            })
        
        return events
    
    def _generate_sleep_events(self, user_id: int, date: datetime) -> List[Dict]:
        """Generate sleep stage data (every 30 min during sleep)."""
        events = []
        
        # Sleep roughly 11 PM - 7 AM
        sleep_start = date.replace(hour=23, minute=0)
        sleep_end = date.replace(hour=7, minute=0) + timedelta(days=1)
        
        # 20% chance of bad sleep night
        is_bad_sleep = random.random() < 0.20
        
        if is_bad_sleep:
            # Shorter sleep
            sleep_duration = np.random.normal(5.5, 0.5)
        else:
            # Normal sleep
            sleep_duration = np.random.normal(7, 1)
        
        sleep_duration = max(4, min(10, sleep_duration))
        sleep_end = sleep_start + timedelta(hours=sleep_duration)
        
        current_time = sleep_start
        cycle = 0
        
        while current_time < sleep_end:
            # 90-min sleep cycles
            cycle_time = current_time
            cycle_end = min(cycle_time + timedelta(minutes=90), sleep_end)
            
            # Realistic cycle: light -> deep -> REM
            stage_sequence = [
                (SleepStage.LIGHT, 20),
                (SleepStage.DEEP, 40),
                (SleepStage.REM, 30)
            ]
            
            elapsed = 0
            for stage, stage_duration in stage_sequence:
                stage_end = min(cycle_time + timedelta(minutes=elapsed + stage_duration), cycle_end)
                
                while cycle_time < stage_end:
                    events.append({
                        "user_id": user_id,
                        "metric_name": MetricName.SLEEP_STAGE,
                        "value": 1,  # Binary: 1 = recorded
                        "time": cycle_time,
                        "metadata": {
                            "stage": stage.value,
                            "data_quality": "good"
                        }
                    })
                    cycle_time += timedelta(minutes=30)
                
                elapsed += stage_duration
            
            current_time = cycle_end
            cycle += 1
        
        return events
    
    def _generate_blood_oxygen_events(self, user_id: int, date: datetime) -> List[Dict]:
        """Generate blood oxygen saturation (every 10 min)."""
        events = []
        hour = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for hour_offset in range(24):
            current_time = hour + timedelta(hours=hour_offset)
            
            # Most of the time: 98%
            base_o2 = 98
            
            # During sleep: slightly lower
            if hour_offset >= 23 or hour_offset < 6:
                base_o2 = 97
            
            for minute in range(0, 60, 10):
                sample_time = current_time.replace(minute=minute)
                value = base_o2 + np.random.normal(0, 0.5)
                value = max(94, min(100, value))
                
                events.append({
                    "user_id": user_id,
                    "metric_name": MetricName.BLOOD_OXYGEN,
                    "value": round(value, 1),
                    "time": sample_time,
                    "metadata": {"data_quality": "good"}
                })
        
        return events
    
    def _generate_workout_events(self, user_id: int, date: datetime) -> List[Dict]:
        """Generate workout events (variable frequency)."""
        events = []
        
        # 3-5 workouts per week
        num_workouts = random.randint(3, 5)
        
        for _ in range(num_workouts):
            # Random time during active hours
            workout_hour = random.randint(6, 20)
            workout_time = date.replace(hour=workout_hour, minute=random.randint(0, 59))
            
            # Duration: 30-90 minutes
            duration = random.randint(30, 90)
            
            events.append({
                "user_id": user_id,
                "metric_name": MetricName.WORKOUT_DURATION,
                "value": float(duration),
                "time": workout_time,
                "metadata": {
                    "type": random.choice(["running", "cycling", "gym", "walking"]),
                    "intensity": random.choice(["low", "moderate", "high"]),
                    "data_quality": "good"
                }
            })
        
        return events
    
    def generate_all_events(self, user_id: int) -> List[Dict]:
        """Generate all metric events for a user across all days."""
        all_events = []
        
        current_date = self.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current_date < self.end_date:
            # Generate all metric types for this day
            all_events.extend(self._generate_heart_rate_events(user_id, current_date))
            all_events.extend(self._generate_steps_events(user_id, current_date))
            all_events.extend(self._generate_sleep_events(user_id, current_date))
            all_events.extend(self._generate_blood_oxygen_events(user_id, current_date))
            all_events.extend(self._generate_workout_events(user_id, current_date))
            
            current_date += timedelta(days=1)
        
        return all_events
    
    def generate_population(self) -> Tuple[List[Dict], List[Dict]]:
        """Generate all users and all their events."""
        users = self.generate_users()
        all_events = []
        
        logger.info(f"Generating events for {self.num_users} users...")
        
        for idx, user in enumerate(users):
            if (idx + 1) % 20 == 0:
                logger.info(f"Generated events for {idx + 1}/{self.num_users} users...")
            
            user_events = self.generate_all_events(idx + 1)
            all_events.extend(user_events)
        
        logger.info(f"Total events generated: {len(all_events)}")
        logger.info(f"Estimated data size: ~{len(all_events) * 0.0003:.1f} MB")
        
        return users, all_events
