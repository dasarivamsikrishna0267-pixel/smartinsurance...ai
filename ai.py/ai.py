Content is user-generated and unverified.
2
# =============================================================================
#  NPC AI DECISION MAKING — How NPCs "think" in a browser/web game
#  Run this in VS Code: open terminal → python npc_ai_explained.py
# =============================================================================

# ── IMPORTS ──────────────────────────────────────────────────────────────────
import random          # Used to add randomness so NPCs don't feel robotic
import time            # Used to simulate real-time ticking (game loop)
import math            # Used for distance calculations between positions

# =============================================================================
#  PART 1 — GAME WORLD SETUP
#  Before an NPC can "think", it needs to know about the world it lives in.
# =============================================================================

# A simple (x, y) grid represents the game map.
# In a real browser game this would be a canvas or tile map in JavaScript.
GRID_WIDTH  = 20   # The map is 20 units wide
GRID_HEIGHT = 10   # The map is 10 units tall

# ── NPC STATES (Finite State Machine) ────────────────────────────────────────
# A Finite State Machine (FSM) is the most popular AI technique for NPCs.
# The NPC can only be in ONE state at a time, and rules decide when to switch.

IDLE    = "IDLE"     # NPC is doing nothing — standing around, breathing
PATROL  = "PATROL"   # NPC is walking its route, keeping watch
CHASE   = "CHASE"    # NPC spotted the player and is running toward them
ATTACK  = "ATTACK"   # NPC is close enough to deal damage
RETREAT = "RETREAT"  # NPC is low on health and running away

# =============================================================================
#  PART 2 — HELPER FUNCTIONS
#  Small reusable tools the NPC AI uses to reason about the world.
# =============================================================================

def distance(pos1, pos2):
    """
    Calculate the straight-line (Euclidean) distance between two positions.
    Positions are (x, y) tuples — e.g., (3, 7).
    
    Formula:  √( (x2-x1)² + (y2-y1)² )
    
    WHY: NPCs need to measure how far away the player is to decide
         whether to chase, attack, or ignore them.
    """
    dx = pos2[0] - pos1[0]   # Horizontal gap between NPC and target
    dy = pos2[1] - pos1[1]   # Vertical gap between NPC and target
    return math.sqrt(dx**2 + dy**2)   # Pythagoras theorem gives the true distance


def clamp(value, min_val, max_val):
    """
    Keep a number inside a valid range.
    e.g., clamp(25, 0, 20) → 20   (can't walk off the map!)
    
    WHY: Stops NPCs from walking outside the game world boundary.
    """
    return max(min_val, min(value, max_val))


def move_toward(current_pos, target_pos, speed=1):
    """
    Take one step from current_pos toward target_pos.
    
    HOW IT WORKS:
      1. Find which direction (angle) points toward the target.
      2. Move 'speed' units in that direction.
      3. Clamp the result so we stay on the map.
    
    WHY: Used by both PATROL (moving to waypoints) and CHASE (chasing the player).
    """
    cx, cy = current_pos          # Unpack current (x, y)
    tx, ty = target_pos           # Unpack target  (x, y)

    angle = math.atan2(ty - cy, tx - cx)   # atan2 gives the angle to the target in radians

    # Move one 'speed' unit along that angle
    new_x = cx + speed * math.cos(angle)   # cos gives the x-component of movement
    new_y = cy + speed * math.sin(angle)   # sin gives the y-component of movement

    # Round to integers (grid-based movement) and keep inside the map
    new_x = clamp(round(new_x), 0, GRID_WIDTH  - 1)
    new_y = clamp(round(new_y), 0, GRID_HEIGHT - 1)

    return (new_x, new_y)   # Return the new position after one step


# =============================================================================
#  PART 3 — THE NPC CLASS
#  This is the brain of the NPC. All decision-making lives here.
# =============================================================================

class NPC:
    """
    Represents one Non-Player Character with its own AI brain.

    Key AI concepts used:
      • Finite State Machine  — decides WHAT the NPC is doing
      • Sensor ranges         — decides WHAT the NPC can perceive
      • Patrol waypoints      — gives the NPC a scripted route
      • Randomness            — makes the NPC feel less predictable
    """

    # ── Constructor ──────────────────────────────────────────────────────────
    def __init__(self, name, position, health=100, patrol_points=None):
        """
        Called when we create a new NPC object.
        Sets up all the NPC's starting values.
        """
        self.name     = name        # The NPC's display name (e.g., "Guard A")
        self.position = position    # Starting (x, y) position on the map
        self.health   = health      # Hit points — 0 means the NPC is dead
        self.max_health = health    # Store the maximum so we can calculate %

        self.state = IDLE           # Every NPC starts idle (FSM initial state)

        # Patrol waypoints — a list of (x,y) positions the NPC walks between
        # If none are given, use two default corners of the map
        self.patrol_points    = patrol_points or [(2, 2), (18, 2), (18, 8), (2, 8)]
        self.patrol_index     = 0   # Which waypoint the NPC is currently heading toward

        # ── Sensor / Perception ranges ────────────────────────────────────
        # NPCs don't have perfect knowledge — they have LIMITED sight.
        self.sight_range  = 6.0    # NPC can SEE  the player within 6 units
        self.attack_range = 1.5    # NPC can HIT  the player within 1.5 units
        self.flee_health  = 25     # If HP drops below 25, the NPC runs away

        # ── Memory ───────────────────────────────────────────────────────
        # Even when the player hides, the NPC remembers where they last were
        self.last_known_player_pos = None   # None = NPC has never seen the player
        self.alert_timer           = 0      # How many ticks remain in "alert" mode

        self.tick_count = 0    # Counts how many AI updates have happened (for logging)

    # ── Perception (can the NPC see/sense the player?) ───────────────────────
    def can_see_player(self, player_pos):
        """
        Returns True if the player is within the NPC's sight_range.
        
        In a real game you'd also check for walls (line-of-sight / raycasting).
        Here we keep it simple: just distance.
        """
        return distance(self.position, player_pos) <= self.sight_range


    def can_attack_player(self, player_pos):
        """
        Returns True if the player is close enough to be attacked.
        The attack range is much smaller than the sight range.
        """
        return distance(self.position, player_pos) <= self.attack_range


    # ── The Decision Engine (Finite State Machine) ───────────────────────────
    def decide_state(self, player_pos, player_alive):
        """
        This is the HEART of the NPC AI.
        
        It reads the current situation (inputs) and decides which
        state the NPC should be in (output).
        
        Think of it as a set of IF/ELSE rules that fire every game tick.
        
        Inputs:
          player_pos   — where the player currently is
          player_alive — is the player still alive?
        
        Output:
          Updates self.state to the correct FSM state.
        """

        # ── Rule 0: If NPC is dead, do nothing ───────────────────────────
        if self.health <= 0:
            self.state = IDLE          # Dead NPCs don't do anything
            return                     # Stop evaluating rules

        # ── Rule 1: Retreat if health is critically low ───────────────────
        # This is checked FIRST because survival overrides everything else.
        if self.health < self.flee_health:
            self.state = RETREAT       # Run! Priority rule — always checked first
            return

        # ── Rule 2: If player is gone / dead, go back to patrolling ───────
        if not player_alive:
            self.state = PATROL        # No threat → resume normal patrol
            return

        # ── Rule 3: Check sensors — can we see the player? ───────────────
        sees_player = self.can_see_player(player_pos)

        if sees_player:
            # Update memory — NPC now knows where the player is
            self.last_known_player_pos = player_pos
            self.alert_timer = 5       # Stay alert for 5 more ticks after losing sight

            # Rule 3a: Close enough to swing a weapon? → ATTACK
            if self.can_attack_player(player_pos):
                self.state = ATTACK
            else:
                # Rule 3b: Can see but not close enough → CHASE
                self.state = CHASE

        # ── Rule 4: Player out of sight but NPC still remembers them ─────
        elif self.alert_timer > 0:
            self.alert_timer -= 1      # Count down the memory timer each tick
            self.state = CHASE         # Keep chasing toward last known position

        # ── Rule 5: No clue where the player is → PATROL ─────────────────
        else:
            self.last_known_player_pos = None   # Memory fades completely
            self.state = PATROL


    # ── Actions (what the NPC physically DOES each tick) ─────────────────────
    def execute_state(self, player_pos):
        """
        Once decide_state() picks a state, execute_state() carries out the action.
        
        Each state maps to a different behaviour:
          IDLE    → Occasionally fidget (small random movement)
          PATROL  → Walk toward the next waypoint
          CHASE   → Run toward the player (or last known position)
          ATTACK  → Deal damage
          RETREAT → Run away from the player
        """

        if self.state == IDLE:
            # ── IDLE behaviour ────────────────────────────────────────────
            # 20% chance each tick of taking a small random step
            # This makes the NPC look "alive" rather than frozen
            if random.random() < 0.2:    # random() returns 0.0–1.0; < 0.2 = 20% chance
                jitter_x = random.randint(-1, 1)   # Step left, right, or stay
                jitter_y = random.randint(-1, 1)   # Step up, down, or stay
                nx = clamp(self.position[0] + jitter_x, 0, GRID_WIDTH  - 1)
                ny = clamp(self.position[1] + jitter_y, 0, GRID_HEIGHT - 1)
                self.position = (nx, ny)
                return f"  💤 fidgeting at {self.position}"
            return "  💤 standing still"


        elif self.state == PATROL:
            # ── PATROL behaviour ──────────────────────────────────────────
            # Move toward the current waypoint; when reached, advance to next
            target_wp = self.patrol_points[self.patrol_index]   # Current waypoint
            self.position = move_toward(self.position, target_wp)

            # If we arrived at the waypoint (close enough), pick the next one
            if distance(self.position, target_wp) < 1.0:
                # Modulo (%) makes the index wrap around: 0→1→2→3→0→...
                self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)

            return f"  🚶 patrolling → waypoint {self.patrol_index} {target_wp} | now at {self.position}"


        elif self.state == CHASE:
            # ── CHASE behaviour ───────────────────────────────────────────
            # Move faster (speed=2) toward the player or last known position
            target = self.last_known_player_pos or player_pos
            self.position = move_toward(self.position, target, speed=2)
            return f"  🏃 chasing → {target} | now at {self.position}"


        elif self.state == ATTACK:
            # ── ATTACK behaviour ──────────────────────────────────────────
            # Deal a random amount of damage each tick
            damage = random.randint(8, 20)    # Roll damage: 8 to 20 points
            return f"  ⚔️  ATTACKING! Dealt {damage} damage to player"


        elif self.state == RETREAT:
            # ── RETREAT behaviour ─────────────────────────────────────────
            # Move AWAY from the player — opposite direction of move_toward
            # We achieve this by pretending the target is on the opposite side
            rx = self.position[0] + (self.position[0] - player_pos[0])
            ry = self.position[1] + (self.position[1] - player_pos[1])
            flee_target = (clamp(rx, 0, GRID_WIDTH-1), clamp(ry, 0, GRID_HEIGHT-1))
            self.position = move_toward(self.position, flee_target, speed=2)
            return f"  💨 RETREATING! Running to {self.position} (HP: {self.health})"

        return "  ❓ unknown state"


    # ── Public tick method — called once per game loop iteration ─────────────
    def update(self, player_pos, player_alive=True):
        """
        Called every game tick (e.g., 10 times per second in a real game).
        
        Steps:
          1. decide_state() → figure out what state to be in
          2. execute_state() → act on that state
          3. Log what happened (useful for debugging in VS Code)
        """
        self.tick_count += 1
        dist_to_player = distance(self.position, player_pos)

        # Step 1: AI decision
        self.decide_state(player_pos, player_alive)

        # Step 2: Execute the chosen behaviour
        action_log = self.execute_state(player_pos)

        # Step 3: Print a detailed status line for each tick
        print(f"[Tick {self.tick_count:>3}] {self.name:<10} | "
              f"State: {self.state:<8} | "
              f"HP: {self.health:>3} | "
              f"Pos: {str(self.position):<10} | "
              f"Dist to player: {dist_to_player:.1f}")
        print(action_log)


    # ── Utility: take damage ──────────────────────────────────────────────────
    def take_damage(self, amount):
        """Reduce the NPC's health. Clamp at 0 so HP never goes negative."""
        self.health = max(0, self.health - amount)
        print(f"  💥 {self.name} took {amount} damage! HP: {self.health}/{self.max_health}")


# =============================================================================
#  PART 4 — DECISION TREE (a second AI technique)
#  A Decision Tree is like a flowchart: ask yes/no questions top-to-bottom,
#  follow the matching branch, reach a leaf = an action.
#  Simpler than an FSM for cases with many independent conditions.
# =============================================================================

def decision_tree_npc(npc_health, player_visible, player_hp, allies_nearby):
    """
    A pure Decision Tree that returns what the NPC should do.
    
    Parameters:
      npc_health     — this NPC's current health (0–100)
      player_visible — can the NPC see the player? (True/False)
      player_hp      — the player's current health (0–100)
      allies_nearby  — are there friendly NPCs close by? (True/False)
    
    Returns a string describing the chosen action.

    Tree structure (read top to bottom):
    
        Is NPC health < 20?
        ├── YES → RETREAT (survive first)
        └── NO  → Can NPC see player?
                  ├── NO  → PATROL (nothing to react to)
                  └── YES → Is player HP < 30?
                            ├── YES → AGGRESSIVE ATTACK (player is weak, push hard)
                            └── NO  → Are allies nearby?
                                      ├── YES → COORDINATED ATTACK (gang up)
                                      └── NO  → CAUTIOUS ATTACK (fight carefully alone)
    """
    # Node 1: Check own survival first
    if npc_health < 20:
        return "🏃 RETREAT — health critical, self-preservation first"

    # Node 2: Can we even see a target?
    if not player_visible:
        return "🚶 PATROL — no target in sight"

    # Node 3: Is the player vulnerable?
    if player_hp < 30:
        return "⚔️  AGGRESSIVE ATTACK — player is weak, press the advantage!"

    # Node 4: Do we have backup?
    if allies_nearby:
        return "🤝 COORDINATED ATTACK — surround the player with allies"

    # Leaf: No special conditions met
    return "🗡️  CAUTIOUS ATTACK — engage player carefully without backup"


# =============================================================================
#  PART 5 — SIMULATION / DEMO
#  Creates NPCs and runs a fake game loop so you can watch the AI tick.
# =============================================================================

def run_simulation():
    print("=" * 70)
    print("  NPC AI SIMULATION — HOW NPCs DECIDE MOVES IN A BROWSER GAME")
    print("=" * 70)
    print()

    # ── Create two NPCs with different patrol routes ──────────────────────
    guard_a = NPC(
        name    = "Guard_A",
        position= (1, 1),        # Starts top-left corner
        health  = 100,
        patrol_points = [(1,1), (10,1), (10,5), (1,5)]   # Rectangle patrol
    )

    guard_b = NPC(
        name    = "Guard_B",
        position= (15, 8),       # Starts bottom-right area
        health  = 40,            # Already low HP — will retreat immediately
        patrol_points = [(15,8), (18,8), (18,2), (15,2)]
    )

    # ── Simulate a player moving across the map ───────────────────────────
    # In a real browser game the player's position would come from keyboard/mouse input.
    # Here we script a path so you can see the AI react to different situations.
    player_path = [
        (1, 9),   # Far away   — NPC should PATROL
        (3, 8),   # Moving closer
        (5, 5),   # Getting near Guard_A's sight range
        (6, 3),   # Inside sight range! → CHASE begins
        (7, 2),   # Still chasing
        (9, 1),   # Very close → ATTACK
        (10,1),   # Right next to Guard_A → ATTACK
        (12,4),   # Player retreats
        (15,7),   # Near Guard_B
        (16,8),   # Right next to Guard_B (low HP → Guard_B will RETREAT)
    ]

    print("── SECTION A: FSM-based NPC (Finite State Machine) ─────────────────\n")

    for step, player_pos in enumerate(player_path):
        print(f"  [Player moved to {player_pos}]")

        # Give Guard_A 15 HP damage at tick 7 to demo ATTACK state damage
        if step == 6:
            guard_a.take_damage(15)

        guard_a.update(player_pos, player_alive=True)

        print()
        time.sleep(0.15)   # Small pause so output is easier to read in VS Code terminal

    print("\n── SECTION B: Guard_B with low HP (demonstrates RETREAT state) ──────\n")
    for player_pos in [(16, 8), (15, 7), (14, 6)]:
        print(f"  [Player moved to {player_pos}]")
        guard_b.update(player_pos, player_alive=True)
        print()
        time.sleep(0.15)

    # ── Decision Tree demo ────────────────────────────────────────────────
    print("\n── SECTION C: Decision Tree AI (separate technique demo) ────────────\n")

    scenarios = [
        # (npc_hp, player_visible, player_hp, allies_nearby, label)
        (80, False, 100, False,  "Scenario 1 — NPC patrolling, player out of sight"),
        (80, True,  100, False,  "Scenario 2 — Player spotted, NPC alone"),
        (80, True,  100, True,   "Scenario 3 — Player spotted, allies nearby"),
        (80, True,  20,  False,  "Scenario 4 — Player is nearly dead"),
        (15, True,  100, True,   "Scenario 5 — NPC critically wounded"),
    ]

    for scenario in scenarios:
        npc_hp, p_vis, p_hp, allies, label = scenario
        result = decision_tree_npc(npc_hp, p_vis, p_hp, allies)
        print(f"  📋 {label}")
        print(f"     Inputs → NPC HP:{npc_hp}  Player visible:{p_vis}  "
              f"Player HP:{p_hp}  Allies:{allies}")
        print(f"     Decision → {result}")
        print()

    # ── Concept summary ───────────────────────────────────────────────────
    print("=" * 70)
    print("  SUMMARY: AI TECHNIQUES USED IN BROWSER/WEB GAME NPCs")
    print("=" * 70)
    concepts = [
        ("Finite State Machine (FSM)",
         "NPC has named states (IDLE, PATROL, CHASE, ATTACK, RETREAT).\n"
         "     Rules fire every tick to switch between them. Used in almost\n"
         "     every game — from Pac-Man ghosts to modern RPG enemies."),
        ("Sensor / Perception radius",
         "NPCs don't see everything — only within sight_range.\n"
         "     Adds stealth gameplay; player can sneak past unaware enemies."),
        ("Memory (alert_timer)",
         "After losing sight of the player, the NPC chases the last known\n"
         "     position for a few ticks before giving up. Feels intelligent."),
        ("Waypoint Patrol",
         "NPCs follow a list of waypoints in a loop, giving them a natural\n"
         "     routine. Easy to script in a level editor."),
        ("Decision Tree",
         "A flowchart of yes/no questions. Easy to tune by designers.\n"
         "     Great for boss encounters with many possible conditions."),
        ("Randomness",
         "Small random jitter in IDLE state + random damage rolls prevent\n"
         "     NPCs from looking like deterministic robots."),
    ]
    for i, (name, desc) in enumerate(concepts, 1):
        print(f"\n  {i}. {name}")
        print(f"     {desc}")

    print("\n" + "=" * 70)
    print("  In a real browser game these algorithms run in JavaScript on the")
    print("  client (or server for multiplayer), ticking ~60 times per second.")
    print("=" * 70)


# =============================================================================
#  ENTRY POINT
#  Python runs this block first. It calls run_simulation() to start everything.
# =============================================================================

if __name__ == "__main__":
    # __name__ equals "__main__" only when YOU run this file directly.
    # If another script imported this file, __name__ would be the module name,
    # and the simulation wouldn't auto-run — that's intentional good practice.
    run_simulation()
