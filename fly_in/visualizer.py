"""Motore di visualizzazione per fly-in."""

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

FONT_SIZE: int = 18
HUD_FONT_SIZE: int = 36
DRONE_FONT_SIZE: int = 28
COUNT_FONT_SIZE: int = 20

# Colors (Pastel Palette)
BG_COLOR: Tuple[int, int, int] = (255, 255, 255)
EDGE_COLOR: Tuple[int, int, int] = (220, 225, 235)
LABEL_COLOR: Tuple[int, int, int] = (150, 150, 150)
HUD_COLOR: Tuple[int, int, int] = (120, 120, 120)
OUTLINE_COLOR: Tuple[int, int, int] = (190, 190, 190)
DRONE_COLOR: Tuple[int, int, int] = (0, 0, 0)
COUNT_COLOR: Tuple[int, int, int] = (0, 0, 0)
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
    """Riproduce le istantanee della simulazione in una finestra pygame.

    Disegna direttamente alla risoluzione nativa con primitive pygame.
    """

    def __init__(
        self,
        map_obj: Map,
        snapshots: List[List[DroneSnapshot]],
    ) -> None:
        """Inizializza il visualizzatore."""
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
        """Mappa le coordinate delle zone in pixel sulla finestra."""
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
        """Ottiene il colore di visualizzazione per una zona."""
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

    def _midpoint(self, z1: str, z2: str) -> Tuple[float, float]:
        """Restituisce il punto medio tra le posizioni di due zone."""
        p1 = self.positions[z1]
        p2 = self.positions[z2]
        return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)

    def _get_drone_pos(
        self,
        prev: DroneSnapshot,
        curr: DroneSnapshot,
        t: float,
    ) -> Tuple[float, float]:
        """Calcola la posizione su schermo interpolata per un drone."""
        # Source position
        if prev.in_flight:
            src = self._midpoint(prev.flight_from, prev.flight_to)
        elif prev.zone is not None:
            p = self.positions[prev.zone]
            src = (float(p[0]), float(p[1]))
        else:
            p = self.positions[self.map.end_zone or ""]
            src = (float(p[0]), float(p[1]))

        # Destination position
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

    def _draw_connections(self, surface: pygame.Surface) -> None:
        """Disegna tutti i collegamenti (archi)."""
        for conn in self.map.connections:
            p1 = self.positions[conn.zone1]
            p2 = self.positions[conn.zone2]
            pygame.draw.line(surface, EDGE_COLOR, p1, p2, 3)

    def _draw_zones(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
    ) -> None:
        """Disegna i cerchi delle zone con contorni ed etichette."""
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

            # Label centered below the zone
            text_surf = font.render(name, True, LABEL_COLOR)
            tx = pos[0] - text_surf.get_width() // 2
            ty = pos[1] + ZONE_RADIUS + 8
            surface.blit(text_surf, (tx, ty))

    def _draw_drones_and_counts(
        self,
        surface: pygame.Surface,
        prev_states: List[DroneSnapshot],
        curr_states: List[DroneSnapshot],
        t: float,
        count_font: pygame.font.Font,
    ) -> None:
        """Disegna i droni in movimento e il conteggio di quelli fermi."""
        zone_counts: Dict[str, int] = {name: 0 for name in self.positions}

        for prev, curr in zip(prev_states, curr_states):
            stayed = (
                not prev.in_flight
                and not curr.in_flight
                and prev.zone == curr.zone
                and prev.zone is not None
            )

            if stayed:
                assert curr.zone is not None
                # Count stationary drones instead of drawing them individually
                zone_counts[curr.zone] += 1
            else:
                # Draw moving drones
                fx, fy = self._get_drone_pos(prev, curr, t)
                x = int(fx) - self.drone_surf.get_width() // 2
                y = int(fy) - self.drone_surf.get_height() // 2
                surface.blit(self.drone_surf, (x, y))

        # Render drone counts inside the zones
        for name, count in zone_counts.items():
            if count > 0:
                count_surf = count_font.render(str(count), True, COUNT_COLOR)
                pos = self.positions[name]
                cx = pos[0] - count_surf.get_width() // 2
                cy = pos[1] - count_surf.get_height() // 2
                surface.blit(count_surf, (cx, cy))

    def _draw_hud(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        turn: int,
        completed: bool,
    ) -> None:
        """Disegna l'overlay HUD (contatore dei turni / completamento)."""
        if completed:
            total = len(self.snapshots) - 1
            text = f"Map OK! Total turns: {total}"
        else:
            text = f"Turn {turn}"

        text_surf = font.render(text, True, HUD_COLOR)
        surface.blit(text_surf, (20, 20))

    # ── Main loop ────────────────────────────────────────────────

    def run(self) -> None:
        """Avvia la finestra pygame e riproduce la simulazione."""
        pygame.init()
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Fly-In")

        font = pygame.font.SysFont("sans-serif", FONT_SIZE, bold=True)
        hud_font = pygame.font.SysFont("sans-serif", HUD_FONT_SIZE, bold=True)
        count_font = pygame.font.SysFont(
            "sans-serif", COUNT_FONT_SIZE, bold=True
        )

        clock = pygame.time.Clock()

        total_snaps = len(self.snapshots)
        playback_idx = 0
        frame_in_turn = 0
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

            # ── Determine interpolation states ───────────────
            if playback_idx == 0:
                prev_states = self.snapshots[0]
                curr_states = self.snapshots[0]
            else:
                prev_states = self.snapshots[playback_idx - 1]
                curr_states = self.snapshots[playback_idx]

            if completed:
                prev_states = self.snapshots[-1]
                curr_states = self.snapshots[-1]

            # ── Render everything directly to the screen ─────
            screen.fill(BG_COLOR)
            self._draw_connections(screen)
            self._draw_zones(screen, font)
            self._draw_drones_and_counts(
                screen, prev_states, curr_states, t, count_font
            )
            self._draw_hud(screen, hud_font, playback_idx, completed)

            pygame.display.flip()

        pygame.quit()
        sys.exit()
