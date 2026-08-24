"""Visualization engine for fly-in."""

import math
import sys
from typing import Dict, List, Tuple

import pygame

from fly_in.parser import Map, Zone
from fly_in.simulator import DroneSnapshot

# ── Constants ────────────────────────────────────────────────────
WINDOW_WIDTH: int = 1280
WINDOW_HEIGHT: int = 720
FPS: int = 60
PADDING_X: int = 100
PADDING_Y: int = 100

ZONE_RADIUS: int = 20
ZONE_OUTLINE_WIDTH: int = 2
ORBIT_RADIUS: float = 35.0
ORBIT_SPEED: float = 2.0

FONT_SIZE: int = 18
HUD_FONT_SIZE: int = 36
DRONE_FONT_SIZE: int = 28

# Colors (Pastel Palette)
BG_COLOR: Tuple[int, int, int] = (255, 255, 255)
EDGE_COLOR: Tuple[int, int, int] = (220, 225, 235)
LABEL_COLOR: Tuple[int, int, int] = (150, 150, 150)
HUD_COLOR: Tuple[int, int, int] = (120, 120, 120)
OUTLINE_COLOR: Tuple[int, int, int] = (190, 190, 190)
DRONE_COLOR: Tuple[int, int, int] = (255, 150, 150)
DEFAULT_ZONE_COLOR: Tuple[int, int, int] = (210, 230, 210)

PASTEL_COLORS: Dict[str, Tuple[int, int, int]] = {
    "green": (200, 235, 200),
    "blue": (200, 220, 255),
    "red": (255, 200, 200),
    "yellow": (255, 255, 200),
    "orange": (255, 225, 200),
    "cyan": (200, 250, 250),
    "purple": (230, 200, 255),
    "grey": (230, 230, 230),
    "gray": (230, 230, 230),
}


class Visualizer:
    """Replays pre-computed simulation snapshots in a pygame window.

    Draws directly to the native resolution with pygame primitives.
    """

    def __init__(
        self,
        map_obj: Map,
        snapshots: List[List[DroneSnapshot]],
    ) -> None:
        """Initialise the visualizer.

        Args:
            map_obj: Parsed map with zones and connections.
            snapshots: Pre-computed list of per-turn drone states.
        """
        self.map: Map = map_obj
        self.snapshots: List[List[DroneSnapshot]] = snapshots
        self.positions: Dict[str, Tuple[int, int]] = (
            self._compute_positions()
        )

        # Pre-render the drone character surface
        pygame.init()
        drone_font = pygame.font.SysFont(
            "segoe ui symbol, dejavu sans, sans-serif",
            DRONE_FONT_SIZE,
            bold=True
        )
        self.drone_surf = drone_font.render("✇", True, DRONE_COLOR)

    # ── Coordinate mapping ───────────────────────────────────────

    def _compute_positions(self) -> Dict[str, Tuple[int, int]]:
        """Map zone coordinates to pixel positions on the window.

        Auto-fits the graph within the window with padding.
        Y-axis is flipped so positive Y points upward on screen.

        Returns:
            Dict mapping zone names to (x, y) pixel tuples.
        """
        zones = self.map.zones
        xs = [z.x for z in zones.values()]
        ys = [z.y for z in zones.values()]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        usable_w = WINDOW_WIDTH - 2 * PADDING_X
        usable_h = WINDOW_HEIGHT - 2 * PADDING_Y

        range_x = max_x - min_x if max_x != min_x else 1
        range_y = max_y - min_y if max_y != min_y else 1

        scale = min(usable_w / range_x, usable_h / range_y)

        graph_w = range_x * scale
        graph_h = range_y * scale
        offset_x = PADDING_X + (usable_w - graph_w) / 2
        offset_y = PADDING_Y + (usable_h - graph_h) / 2

        positions: Dict[str, Tuple[int, int]] = {}
        for name, zone in zones.items():
            px = offset_x + (zone.x - min_x) * scale
            py = offset_y + (max_y - zone.y) * scale
            positions[name] = (int(px), int(py))
        return positions

    # ── Color helpers ────────────────────────────────────────────

    @staticmethod
    def _resolve_color(zone: Zone) -> Tuple[int, int, int]:
        """Get the display color for a zone.

        Args:
            zone: The zone to resolve color for.

        Returns:
            An RGB color tuple.
        """
        if zone.color:
            color_name = zone.color.lower()
            if color_name in PASTEL_COLORS:
                return PASTEL_COLORS[color_name]
            try:
                c = pygame.Color(color_name)
                # Blend with white to make it pastel if not recognized
                return (
                    (c.r + 255) // 2,
                    (c.g + 255) // 2,
                    (c.b + 255) // 2
                )
            except ValueError:
                pass
        return DEFAULT_ZONE_COLOR

    # ── Drone position helpers ───────────────────────────────────

    def _orbit_pos(
        self,
        center: Tuple[int, int],
        elapsed: float,
        drone_id: int,
    ) -> Tuple[float, float]:
        """Compute a circular orbit position around a center.

        Args:
            center: Pixel center of the orbit.
            elapsed: Total elapsed time in seconds.
            drone_id: Used to offset phase so drones don't overlap.

        Returns:
            Float (x, y) on the orbit circle.
        """
        phase = drone_id * (2.0 * math.pi / 8.0)
        angle = elapsed * ORBIT_SPEED + phase
        ox = center[0] + ORBIT_RADIUS * math.cos(angle)
        oy = center[1] + ORBIT_RADIUS * math.sin(angle)
        return (ox, oy)

    def _midpoint(
        self, z1: str, z2: str,
    ) -> Tuple[float, float]:
        """Return the midpoint between two zone positions.

        Args:
            z1: First zone name.
            z2: Second zone name.

        Returns:
            (x, y) midpoint as floats.
        """
        p1 = self.positions[z1]
        p2 = self.positions[z2]
        return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)

    def _get_drone_pos(
        self,
        prev: DroneSnapshot,
        curr: DroneSnapshot,
        t: float,
        elapsed: float,
        playback_idx: int,
    ) -> Tuple[float, float]:
        """Compute interpolated screen position for a drone.

        Returns float coordinates for smooth sub-pixel movement.
        Connects linear movement perfectly to the orbital path.

        Args:
            prev: Drone state at the previous turn.
            curr: Drone state at the current turn.
            t: Interpolation factor 0.0 to 1.0 within the turn.
            elapsed: Total elapsed seconds (for continuous orbit).
            playback_idx: The integer turn index for orbit transitions.

        Returns:
            Float (x, y) on the window.
        """
        # Determine if the drone stayed in place
        stayed = (
            not prev.in_flight
            and not curr.in_flight
            and prev.zone is not None
            and curr.zone is not None
            and prev.zone == curr.zone
        )
        if stayed:
            assert curr.zone is not None
            center = self.positions[curr.zone]
            return self._orbit_pos(center, elapsed, curr.drone_id)

        # Source position (center of the zone)
        if prev.in_flight:
            src = self._midpoint(prev.flight_from, prev.flight_to)
        elif prev.zone is not None:
            p = self.positions[prev.zone]
            src = (float(p[0]), float(p[1]))
        else:
            p = self.positions[self.map.end_zone or ""]
            src = (float(p[0]), float(p[1]))

        # Destination position (center of the zone)
        if curr.in_flight:
            dst = self._midpoint(curr.flight_from, curr.flight_to)
        elif curr.zone is not None:
            p = self.positions[curr.zone]
            dst = (float(p[0]), float(p[1]))
        else:
            p = self.positions[self.map.end_zone or ""]
            dst = (float(p[0]), float(p[1]))

        x = src[0] + (dst[0] - src[0]) * t
        y = src[1] + (dst[1] - src[1]) * t
        return (x, y)

    # ── Drawing primitives ───────────────────────────────────────

    def _draw_drone(
        self, surface: pygame.Surface, fx: float, fy: float,
    ) -> None:
        """Draw a drone character using the pre-rendered surface.

        Args:
            surface: Display surface.
            fx: x coordinate (float).
            fy: y coordinate (float).
        """
        x = int(fx) - self.drone_surf.get_width() // 2
        y = int(fy) - self.drone_surf.get_height() // 2
        surface.blit(self.drone_surf, (x, y))

    def _draw_connections(self, surface: pygame.Surface) -> None:
        """Draw all connection edges.

        Args:
            surface: Surface to draw on.
        """
        for conn in self.map.connections:
            p1 = self.positions[conn.zone1]
            p2 = self.positions[conn.zone2]
            pygame.draw.line(surface, EDGE_COLOR, p1, p2, 3)

    def _draw_zones(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
    ) -> None:
        """Draw zone circles with outlines and labels.

        Args:
            surface: Surface to draw on.
            font: Font for zone labels.
        """
        for name, pos in self.positions.items():
            zone = self.map.zones[name]
            color = self._resolve_color(zone)

            # Filled zone circle
            pygame.draw.circle(surface, color, pos, ZONE_RADIUS)

            # Outline circle
            pygame.draw.circle(
                surface, OUTLINE_COLOR, pos,
                ZONE_RADIUS, ZONE_OUTLINE_WIDTH
            )

            # Label centered below the zone (anti-aliased, grey)
            text_surf = font.render(name, True, LABEL_COLOR)
            tx = pos[0] - text_surf.get_width() // 2
            ty = pos[1] + ZONE_RADIUS + 8
            surface.blit(text_surf, (tx, ty))

    def _draw_drones(
        self,
        surface: pygame.Surface,
        prev_states: List[DroneSnapshot],
        curr_states: List[DroneSnapshot],
        t: float,
        elapsed: float,
        playback_idx: int,
    ) -> None:
        """Draw all drones.

        Args:
            surface: Display surface.
            prev_states: Drone states from the previous snapshot.
            curr_states: Drone states from the current snapshot.
            t: Interpolation factor within the current turn.
            elapsed: Total elapsed seconds.
            playback_idx: The integer turn index for transition math.
        """
        for prev, curr in zip(prev_states, curr_states):
            fx, fy = self._get_drone_pos(
                prev, curr, t, elapsed, playback_idx
            )
            self._draw_drone(surface, fx, fy)

    def _draw_hud(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        turn: int,
        completed: bool,
    ) -> None:
        """Draw the HUD overlay (turn counter / completion).

        Args:
            surface: Surface to draw on.
            font: Font for HUD text.
            turn: Current turn number.
            completed: Whether the simulation has finished.
        """
        if completed:
            total = len(self.snapshots) - 1
            text = f"Map completed! Total turns: {total}"
        else:
            text = f"Turn {turn}"

        text_surf = font.render(text, True, HUD_COLOR)
        surface.blit(text_surf, (20, 20))

    # ── Main loop ────────────────────────────────────────────────

    def run(self) -> None:
        """Launch the pygame window and replay the simulation."""
        pygame.init()
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Fly-In")

        # Use a smooth anti-aliased font
        font = pygame.font.SysFont("sans-serif", FONT_SIZE, bold=True)
        hud_font = pygame.font.SysFont(
            "sans-serif", HUD_FONT_SIZE, bold=True
        )

        clock = pygame.time.Clock()

        total_snaps = len(self.snapshots)
        playback_idx = 0
        frame_in_turn = 0
        total_frames = 0
        completed = False

        running = True
        while running:
            clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # ── Advance playback ─────────────────────────────
            if not completed:
                frame_in_turn += 1
                if frame_in_turn >= FPS:
                    frame_in_turn = 0
                    if playback_idx < total_snaps - 1:
                        playback_idx += 1
                    else:
                        completed = True

            t = frame_in_turn / float(FPS)

            # Deterministic elapsed time ensures orbits are smooth
            # and perfectly synchronized with the playback timeline.
            total_frames += 1
            elapsed = total_frames / float(FPS)

            # ── Determine interpolation states ───────────────
            if playback_idx == 0:
                prev_states = self.snapshots[0]
                curr_states = self.snapshots[0]
            else:
                prev_states = self.snapshots[playback_idx - 1]
                curr_states = self.snapshots[playback_idx]

            # For completed state, drones continue to orbit at final pos
            if completed:
                prev_states = self.snapshots[-1]
                curr_states = self.snapshots[-1]

            # ── Render everything directly to the screen ─────
            screen.fill(BG_COLOR)
            self._draw_connections(screen)
            self._draw_zones(screen, font)
            self._draw_drones(
                screen, prev_states, curr_states, t, elapsed, playback_idx
            )
            self._draw_hud(screen, hud_font, playback_idx, completed)

            pygame.display.flip()

        pygame.quit()
        sys.exit()
