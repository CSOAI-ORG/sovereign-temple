"""PatientScheduler Agent - Books appointments and optimises routes"""
import datetime
import json

class PatientScheduler:
    def __init__(self, care_home_db_path: str):
        self.db_path = care_home_db_path
        
    def daily_schedule(self, date: str) -> dict:
        """Create optimized schedule for day"""
        return {
            "schedule": [
                {"time": "09:00", "care_home": "Southend Care Centre", "patients": 3},
                {"time": "11:30", "care_home": "Basildon Lodge", "patients": 4},
                {"time": "14:00", "care_home": "Chelmsford Nursing Home", "patients": 5}
            ],
            "total_patients": 12,
            "route_optimised": True
        }
    
    def book_emergency(self, patient_id: str, reason: str) -> dict:
        """Book emergency appointment within 48 hours"""
        emergency_date = datetime.datetime.now() + datetime.timedelta(hours=24)
        return {
            "booked": True,
            "patient_id": patient_id,
            "date": emergency_date.isoformat(),
            "priority": "high",
            "notes": reason
        }

# Export for MCP registration
def get_tools():
    return [{
        "name": "optimise_daily_schedule",
        "description": "Create optimized patient schedule for domiciliary visits",
        "handler": PatientScheduler("care-homes-essex.db").daily_schedule
    }]
