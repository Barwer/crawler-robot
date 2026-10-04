import cv2
import numpy as np
import math
import time
import cv2.aruco as aruco

class ArucoTracker:
    def __init__(self, camera_index=0, capture=None):
        self.current_frame = 0
        
        self.cap = capture if capture is not None else cv2.VideoCapture(camera_index)

        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        self.parameters = aruco.DetectorParameters()
        self.parameters.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX
        self.detector = aruco.ArucoDetector(self.aruco_dict, self.parameters)
        self.detected_ids = []
        self.start_world = (0, 0)
        self.real_distance = {}
        self.real_world_pts = np.array([
            [0, 0], [0, 8], [8, 8], [8, 0]
        ], dtype=np.float32)
        # Robot 1 uses marker 1; robot 2 uses marker 2.
        self.target_ids = [1, 2]
        self.positions = {marker_id: [] for marker_id in self.target_ids}

    def pixel_to_world(self, point_px, H):
        px = np.array([[point_px[0]], [point_px[1]], [1]])
        world = np.dot(H, px)
        world = world / world[2]
        return (world[0][0], world[1][0])

    def close(self):
        self.cap.release()

    def update_frame(self, measure=True):
        ret, frame = self.cap.read()
        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = self.detector.detectMarkers(gray)
            self.detected_ids = [] if ids is None else [int(value) for value in ids.flatten()]
            self.current_frame += 1
            # print(self.current_frame)

            if ids is not None:
                for i, marker_id in enumerate(ids.flatten()):
                    if marker_id in self.target_ids:
                        corner = corners[i][0]
                        cx = int(np.mean(corner[:, 0]))
                        cy = int(np.mean(corner[:, 1]))

                        # เก็บตำแหน่งใน dictionary แยกตาม marker_id
                        if marker_id not in self.positions:
                            self.positions[marker_id] = []
                        if measure:
                            self.positions[marker_id].append((cx, cy))

                        # วาด marker
                        for j in range(4):
                            pt1 = tuple(corner[j].astype(int))
                            pt2 = tuple(corner[(j + 1) % 4].astype(int))
                            cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

                        cv2.putText(frame, f"ID {marker_id}", (cx + 10, cy),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                        # ต้องมีตำแหน่งมากกว่า 1 จุดถึงจะคำนวณระยะได้
                        if measure and len(self.positions[marker_id]) >= 2:
                            image_pts = corners[i][0].astype(np.float32)
                            H, _ = cv2.findHomography(image_pts, self.real_world_pts)

                            start_world = self.pixel_to_world(self.positions[marker_id][0], H)
                            end_world = self.pixel_to_world(self.positions[marker_id][-1], H)

                            dx = end_world[0] - start_world[0]
                            dy = end_world[1] - start_world[1]
                            distance = math.hypot(dx, dy)

                            # ใช้จุดจริงจาก marker ในการหาทิศทาง
                            direction_vector = corner[1] - corner[0]
                            direction_vector = direction_vector / np.linalg.norm(direction_vector)

                            movement_vector = np.array(end_world) - np.array(start_world)
                            dot_product = np.dot(movement_vector, direction_vector)

                            # บันทึกระยะใน dictionary ตาม marker_id
                            if not hasattr(self, 'real_distance'):
                                self.real_distance = {}
                            self.real_distance[marker_id] = distance if dot_product >= 0 else -distance

                            # ล้างตำแหน่งของ marker นี้
                            self.positions[marker_id] = []
            elif measure:
                self.real_distance = {marker_id: 0 for marker_id in self.target_ids}

            found = ", ".join(map(str, self.detected_ids)) or "none"
            missing = [value for value in self.target_ids if value not in self.detected_ids]
            color = (0, 180, 0) if not missing else (0, 0, 255)
            cv2.putText(frame, f"DICT_4X4_50 | detected: {found} | target: 1, 2",
                        (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame
        self.detected_ids = []
        return None

    def get_distance(self):
        return self.real_distance
    
    def get_start_world(self):
        self.positions = {marker_id: [] for marker_id in self.target_ids}
        self.real_distance = {marker_id: 0 for marker_id in self.target_ids}
        ret, frame = self.cap.read()
        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = self.detector.detectMarkers(gray)

            if ids is not None:
                for i, marker_id in enumerate(ids.flatten()):
                    if marker_id in self.target_ids:
                        # print(marker_id)
                        corner = corners[i][0]
                        cx = int(np.mean(corner[:, 0]))
                        cy = int(np.mean(corner[:, 1]))

                        if marker_id not in self.positions:
                            self.positions[marker_id] = []
                        self.positions[marker_id].append((cx, cy))
# Import alias for existing code; tracker no longer creates UI widgets.
ArucoTrackerApp = ArucoTracker
