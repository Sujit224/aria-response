class CameraManager:
    """Stub for the vision camera manager so the backend can start up."""
    
    def __init__(self, venue_id: str):
        self.venue_id = venue_id

    async def start(self):
        print(f"[VISION] Starting CameraManager for venue {self.venue_id} (Stub)")

    async def stop(self):
        print(f"[VISION] Stopping CameraManager for venue {self.venue_id} (Stub)")
