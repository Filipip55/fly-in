import pygame
import sys
import json
import math

# Configuration
VIRTUAL_WIDTH, VIRTUAL_HEIGHT = 320, 180  # Low-res internal canvas
SCALE_FACTOR = 4                           # Output: 1280x720
FPS = 60

# --- 1. Parser ---
def parse_graph_data(json_str: str):
    """Parses node positions and edge definitions from structured text/JSON."""
    data = json.loads(json_str)
    nodes = {k: pygame.Vector2(v[0], v[1]) for k, v in data["nodes"].items()}
    edges = data["edges"]
    routes = data["routes"]
    return nodes, edges, routes

# --- 2. Simulation Entities ---
class Drone:
    def __init__(self, route, speed=1.0):
        self.route = route              # List of node keys, e.g., ["A", "B", "C", "A"]
        self.current_step = 0
        self.speed = speed
        self.pos = None
        self.target_pos = None

    def update(self, nodes):
        if not self.route:
            return
        
        current_node = self.route[self.current_step]
        next_node = self.route[(self.current_step + 1) % len(self.route)]
        
        if self.pos is None:
            self.pos = pygame.Vector2(nodes[current_node])
        
        target = nodes[next_node]
        direction = target - self.pos
        distance = direction.length()
        
        if distance <= self.speed:
            self.pos = pygame.Vector2(target)
            self.current_step = (self.current_step + 1) % len(self.route)
        else:
            self.pos += direction.normalize() * self.speed

    def draw(self, surface):
        if self.pos:
            # Draw a 3x3 pixel square representing the drone
            rect = pygame.Rect(int(self.pos.x) - 1, int(self.pos.y) - 1, 3, 3)
            pygame.draw.rect(surface, (255, 60, 60), rect)

# --- 3. Main Loop ---
def main():
    pygame.init()
    
    # Target display window
    screen = pygame.display.set_mode((VIRTUAL_WIDTH * SCALE_FACTOR, VIRTUAL_HEIGHT * SCALE_FACTOR))
    pygame.display.set_caption("Drone Simulation [Bitmap Engine]")
    
    # Internal low-res pixel canvas
    canvas = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
    
    font = pygame.font.SysFont("monospace", 8)  # Fallback to monospace; use a .ttf pixel font for best results
    clock = pygame.time.Clock()

    # Sample parsed graph input
    sample_input = """
    {
        "nodes": {
            "A": [30, 40],
            "B": [120, 30],
            "C": [200, 90],
            "D": [100, 140],
            "E": [280, 150]
        },
        "edges": [
            ["A", "B"], ["B", "C"], ["C", "D"], 
            ["D", "A"], ["C", "E"], ["B", "D"]
        ],
        "routes": [
            ["A", "B", "C", "D", "A"],
            ["C", "E", "C", "B", "D", "C"]
        ]
    }
    """
    nodes, edges, routes = parse_graph_data(sample_input)
    drones = [Drone(r, speed=0.75) for r in routes]

    running = True
    while running:
        clock.tick(FPS)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- Update Simulation ---
        for drone in drones:
            drone.update(nodes)

        # --- Render to Low-Res Canvas ---
        canvas.fill((20, 24, 30))  # Dark background

        # Draw graph edges
        for start_key, end_key in edges:
            start_pos = nodes[start_key]
            end_pos = nodes[end_key]
            pygame.draw.line(canvas, (60, 70, 90), (int(start_pos.x), int(start_pos.y)), (int(end_pos.x), int(end_pos.y)), 1)

        # Draw graph nodes & labels
        for key, pos in nodes.items():
            # 4x4 Node rectangle
            pygame.draw.rect(canvas, (100, 200, 120), (int(pos.x) - 2, int(pos.y) - 2, 4, 4))
            # Aliased text (antialias=False)
            text_surf = font.render(key, False, (200, 200, 200))
            canvas.blit(text_surf, (int(pos.x) + 4, int(pos.y) - 4))

        # Draw drones
        for drone in drones:
            drone.draw(canvas)

        # --- Upscale to Screen ---
        upscaled = pygame.transform.scale(canvas, (VIRTUAL_WIDTH * SCALE_FACTOR, VIRTUAL_HEIGHT * SCALE_FACTOR))
        screen.blit(upscaled, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()