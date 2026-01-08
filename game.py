import pygame
import math
import random

# --- CONFIGURATION & ESTHÉTIQUE ---
WIDTH, HEIGHT = 1000, 750
MAP_SIZE = 2000
FPS = 60

# Palette de couleurs
C_LAND = (50, 60, 50)       # Sol foncé
C_GRID = (60, 70, 60)       # Grille discrète
C_OBSTACLE = (40, 40, 40)   # Rochers
C_TREE = (20, 100, 40)      # Arbres (cercle extérieur)
C_TREE_C = (30, 120, 50)    # Arbres (centre)
C_STORM = (100, 0, 255)     # Tempête
C_HEALTH = (0, 255, 100)    # Kits de soin

class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0, 0)
        self.shake = 0

    def update(self, target):
        # Suivi fluide (Lerp)
        target_x = target.pos.x - WIDTH // 2
        target_y = target.pos.y - HEIGHT // 2
        self.offset.x += (target_x - self.offset.x) * 0.1
        self.offset.y += (target_y - self.offset.y) * 0.1
        
        # Shake effect (tremblement)
        if self.shake > 0:
            self.offset.x += random.randint(-int(self.shake), int(self.shake))
            self.offset.y += random.randint(-int(self.shake), int(self.shake))
            self.shake -= 1

class Particle:
    def __init__(self, x, y, color, speed, lifetime):
        self.pos = pygame.Vector2(x, y)
        angle = random.uniform(0, 6.28)
        self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
        self.color = color
        self.life = lifetime
        self.max_life = lifetime

    def update(self):
        self.pos += self.vel
        self.life -= 1
        self.vel *= 0.9 # Friction

    def draw(self, surf, cam_offset):
        if self.life > 0:
            alpha = int((self.life / self.max_life) * 255)
            s = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (2, 2), 2)
            surf.blit(s, (self.pos.x - cam_offset.x, self.pos.y - cam_offset.y))

class Obstacle:
    def __init__(self, x, y, radius, type_):
        self.pos = pygame.Vector2(x, y)
        self.radius = radius
        self.type = type_ # 'rock' (bloque les balles) ou 'tree' (cache le joueur)

    def draw(self, surf, cam_offset):
        screen_pos = (int(self.pos.x - cam_offset.x), int(self.pos.y - cam_offset.y))
        if self.type == 'rock':
            pygame.draw.circle(surf, (30, 30, 30), (screen_pos[0]+5, screen_pos[1]+5), self.radius) # Ombre
            pygame.draw.circle(surf, C_OBSTACLE, screen_pos, self.radius)
            pygame.draw.circle(surf, (60, 60, 60), screen_pos, self.radius - 5)
        else: # Tree
            pygame.draw.circle(surf, (15, 80, 30), (screen_pos[0]+10, screen_pos[1]+10), self.radius) # Ombre
            pygame.draw.circle(surf, C_TREE, screen_pos, self.radius)
            pygame.draw.circle(surf, C_TREE_C, screen_pos, self.radius - 15)

class Item:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.radius = 15
        self.bob = 0

    def draw(self, surf, cam_offset):
        self.bob += 0.1
        scale = 15 + math.sin(self.bob) * 2
        screen_pos = (int(self.pos.x - cam_offset.x), int(self.pos.y - cam_offset.y))
        pygame.draw.circle(surf, C_HEALTH, screen_pos, int(scale))
        # Petite croix blanche
        pygame.draw.line(surf, (255,255,255), (screen_pos[0]-5, screen_pos[1]), (screen_pos[0]+5, screen_pos[1]), 3)
        pygame.draw.line(surf, (255,255,255), (screen_pos[0], screen_pos[1]-5), (screen_pos[0], screen_pos[1]+5), 3)

class Bullet:
    def __init__(self, x, y, angle, owner_id):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * 18
        self.owner_id = owner_id
        self.life = 60

    def update(self):
        self.pos += self.vel
        self.life -= 1

    def draw(self, surf, cam_offset):
        start = self.pos - self.vel.normalize() * 10
        pygame.draw.line(surf, (255, 255, 200), 
                         (start.x - cam_offset.x, start.y - cam_offset.y), 
                         (self.pos.x - cam_offset.x, self.pos.y - cam_offset.y), 3)

class Entity:
    _id_counter = 0
    def __init__(self, x, y, color):
        self.id = Entity._id_counter
        Entity._id_counter += 1
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.color = color
        self.health = 100
        self.max_health = 100
        self.radius = 22
        self.angle = 0
        self.cooldown = 0

    def move_and_slide(self, obstacles):
        # Physique simple avec friction
        self.pos += self.vel
        self.vel *= 0.85 # Friction
        
        # Collisions Murs/Obstacles
        for obs in obstacles:
            if obs.type == 'rock':
                dist = self.pos.distance_to(obs.pos)
                min_dist = self.radius + obs.radius
                if dist < min_dist:
                    push = (self.pos - obs.pos).normalize() * (min_dist - dist)
                    self.pos += push

        # Limites Map
        self.pos.x = max(25, min(MAP_SIZE-25, self.pos.x))
        self.pos.y = max(25, min(MAP_SIZE-25, self.pos.y))

    def draw(self, surf, cam_offset):
        screen_pos = (int(self.pos.x - cam_offset.x), int(self.pos.y - cam_offset.y))
        
        # Corps
        pygame.draw.circle(surf, (0,0,0), (screen_pos[0]+2, screen_pos[1]+2), self.radius) # Ombre
        pygame.draw.circle(surf, self.color, screen_pos, self.radius)
        
        # Mains / Arme
        hand_offset = pygame.Vector2(math.cos(self.angle), math.sin(self.angle)) * 30
        hand_pos = (screen_pos[0] + hand_offset.x, screen_pos[1] + hand_offset.y)
        pygame.draw.circle(surf, (20,20,20), (int(hand_pos[0]), int(hand_pos[1])), 10) # Main
        
        # Barre de vie
        if self.health < self.max_health:
            rect_bg = (screen_pos[0]-25, screen_pos[1]-40, 50, 6)
            rect_fg = (screen_pos[0]-25, screen_pos[1]-40, (self.health/self.max_health)*50, 6)
            pygame.draw.rect(surf, (50,0,0), rect_bg)
            pygame.draw.rect(surf, (0,255,0), rect_fg)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("FORTNITE 2D - ULTIMATE FIX")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Segoe UI", 30, bold=True)
        self.cam = Camera()
        self.reset_game()

    def reset_game(self):
        self.player = Entity(MAP_SIZE//2, MAP_SIZE//2, (0, 150, 255))
        self.bots = [Entity(random.randint(100, MAP_SIZE-100), random.randint(100, MAP_SIZE-100), (255, 60, 60)) for _ in range(15)]
        self.obstacles = []
        self.items = []
        self.bullets = []
        self.particles = []
        
        # Génération procédurale
        for _ in range(40):
            self.obstacles.append(Obstacle(random.randint(0, MAP_SIZE), random.randint(0, MAP_SIZE), random.randint(30, 60), 'rock'))
        for _ in range(60):
            self.obstacles.append(Obstacle(random.randint(0, MAP_SIZE), random.randint(0, MAP_SIZE), random.randint(50, 90), 'tree'))
        for _ in range(20):
            self.items.append(Item(random.randint(100, MAP_SIZE-100), random.randint(100, MAP_SIZE-100)))

        self.storm_center = pygame.Vector2(MAP_SIZE//2, MAP_SIZE//2)
        self.storm_radius = MAP_SIZE // 1.1
        self.state = "PLAYING" # PLAYING, WIN, LOSE
        self.kills = 0

    def shoot(self, shooter):
        if shooter.cooldown <= 0:
            spread = random.uniform(-0.1, 0.1) if shooter != self.player else 0
            b = Bullet(shooter.pos.x, shooter.pos.y, shooter.angle + spread, shooter.id)
            self.bullets.append(b)
            shooter.cooldown = 15 if shooter == self.player else 50
            
            # Recul
            recoil = pygame.Vector2(math.cos(shooter.angle), math.sin(shooter.angle)) * -4
            shooter.vel += recoil
            if shooter == self.player:
                self.cam.shake = 5

    def update(self):
        if self.state != "PLAYING": return

        # 1. INPUT JOUEUR
        keys = pygame.key.get_pressed()
        accel = pygame.Vector2(0,0)
        speed = 1.5
        if keys[pygame.K_z]: accel.y = -speed
        if keys[pygame.K_s]: accel.y = speed
        if keys[pygame.K_q]: accel.x = -speed
        if keys[pygame.K_d]: accel.x = speed
        
        self.player.vel += accel
        mx, my = pygame.mouse.get_pos()
        # Correction souris : on prend en compte l'offset de la caméra
        self.player.angle = math.atan2(my + self.cam.offset.y - self.player.pos.y, mx + self.cam.offset.x - self.player.pos.x)
        
        if pygame.mouse.get_pressed()[0]:
            self.shoot(self.player)

        # 2. LOGIQUE BOTS
        all_entities = [self.player] + self.bots
        for bot in self.bots:
            targets = [e for e in all_entities if e.id != bot.id and e.health > 0]
            if targets:
                target = min(targets, key=lambda t: bot.pos.distance_to(t.pos))
                dist = bot.pos.distance_to(target.pos)

                if bot.pos.distance_to(self.storm_center) > self.storm_radius - 100:
                    delta = (self.storm_center - bot.pos).normalize()
                    bot.vel += delta * 0.8
                    bot.angle = math.atan2(delta.y, delta.x)
                
                elif dist < 500:
                    delta = (target.pos - bot.pos)
                    bot.angle = math.atan2(delta.y, delta.x)
                    if dist > 200:
                        bot.vel += delta.normalize() * 0.8
                    
                    # Tirer seulement si pas d'obstacle évident (simplifié)
                    self.shoot(bot)
                
                else:
                    if random.random() < 0.02:
                        bot.temp_dir = pygame.Vector2(random.uniform(-1,1), random.uniform(-1,1))
                    if hasattr(bot, 'temp_dir'):
                         bot.vel += bot.temp_dir * 0.5

        # 3. PHYSIQUE & UPDATE ENTITÉS
        for e in all_entities:
            e.move_and_slide(self.obstacles)
            e.cooldown -= 1
            
            if e.pos.distance_to(self.storm_center) > self.storm_radius:
                e.health -= 0.3
            
            for item in self.items[:]:
                if e.pos.distance_to(item.pos) < e.radius + item.radius:
                    if e.health < 100:
                        e.health = min(100, e.health + 50)
                        self.items.remove(item)
                        for _ in range(10):
                            self.particles.append(Particle(e.pos.x, e.pos.y, (50, 255, 50), 3, 30))

        # 4. BALLES & COLLISIONS
        for b in self.bullets[:]:
            b.update()
            removed = False
            
            for obs in self.obstacles:
                if obs.type == 'rock' and b.pos.distance_to(obs.pos) < obs.radius:
                    self.bullets.remove(b)
                    removed = True
                    for _ in range(5):
                        self.particles.append(Particle(b.pos.x, b.pos.y, (100,100,100), 2, 20))
                    break
            if removed: continue

            for e in all_entities:
                if b.owner_id != e.id and b.pos.distance_to(e.pos) < e.radius:
                    e.health -= 15
                    e.vel += b.vel.normalize() * 3 
                    
                    for _ in range(8):
                        self.particles.append(Particle(b.pos.x, b.pos.y, (200, 0, 0), 4, 20))
                    
                    if b in self.bullets: self.bullets.remove(b)
                    
                    if e.health <= 0:
                        if e == self.player:
                            self.state = "LOSE"
                        elif e in self.bots:
                            self.bots.remove(e)
                            if b.owner_id == self.player.id:
                                self.kills += 1
                                self.items.append(Item(e.pos.x, e.pos.y))
                    break
            
            if not removed and b.life <= 0 and b in self.bullets:
                self.bullets.remove(b)

        # 5. NETTOYAGE
        for p in self.particles[:]:
            p.update()
            if p.life <= 0: self.particles.remove(p)

        self.storm_radius -= 0.1
        self.cam.update(self.player)
        
        if len(self.bots) == 0:
            self.state = "WIN"

    def draw(self):
        self.screen.fill(C_LAND)
        cx, cy = self.cam.offset.x, self.cam.offset.y

        # Grille
        for x in range(0, MAP_SIZE, 100):
            pygame.draw.line(self.screen, C_GRID, (x-cx, -cy), (x-cx, MAP_SIZE-cy))
        for y in range(0, MAP_SIZE, 100):
            pygame.draw.line(self.screen, C_GRID, (-cx, y-cy), (MAP_SIZE-cx, y-cy))

        # IMPORTANT : On passe self.cam.offset (le Vecteur) et pas self.cam (la Classe)
        for i in self.items: i.draw(self.screen, self.cam.offset)
        for p in self.particles: p.draw(self.screen, self.cam.offset)

        for b in self.bots: b.draw(self.screen, self.cam.offset)
        self.player.draw(self.screen, self.cam.offset)
        for b in self.bullets: b.draw(self.screen, self.cam.offset)

        # Z-sorting (pour dessiner les obstacles "devant" ou "derrière" selon Y)
        visible_obs = [o for o in self.obstacles if abs(o.pos.x - self.player.pos.x) < WIDTH and abs(o.pos.y - self.player.pos.y) < HEIGHT]
        for obs in visible_obs:
            obs.draw(self.screen, self.cam.offset)

        # Tempête
        storm_s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(storm_s, (*C_STORM, 60), (int(self.storm_center.x - cx), int(self.storm_center.y - cy)), int(self.storm_radius), width=2000)
        self.screen.blit(storm_s, (0,0))

        # UI
        if self.state == "PLAYING":
            alive_txt = self.font.render(f"EN VIE: {len(self.bots)+1}", True, (255, 255, 255))
            kill_txt = self.font.render(f"KILLS: {self.kills}", True, (255, 50, 50))
            self.screen.blit(alive_txt, (WIDTH-200, 20))
            self.screen.blit(kill_txt, (WIDTH-200, 60))
        
        elif self.state == "WIN":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 200, 0, 100))
            self.screen.blit(overlay, (0,0))
            txt = self.font.render("VICTOIRE ROYALE !", True, (255, 255, 255))
            self.screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2))
            
        elif self.state == "LOSE":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((200, 0, 0, 100))
            self.screen.blit(overlay, (0,0))
            txt = self.font.render("ÉLIMINÉ - APPUIE SUR R", True, (255, 255, 255))
            self.screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r and self.state != "PLAYING":
                        self.reset_game()

            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    Game().run()