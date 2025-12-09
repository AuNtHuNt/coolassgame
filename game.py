import pygame
import random
import os
import sys

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Простейший Платформер")

WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

FPS = 60
TILE_SIZE = 50
GRAVITY = 0.8
PLAYER_SPEED = 5
ENEMY_SPEED = 3

PLAYER_JUMP_POWER = -20 
ENEMY_JUMP_POWER = -18 

MAX_JUMP_HEIGHT = 200 
MAX_RUN_DISTANCE = 300 

SCORE_THRESHOLD_FOR_REGEN = 50 

PLAYER_SCALE = 1.0
ENEMY_SCALE = 1.0
COIN_SCALE = 0.3

ASSETS_DIR = 'assets'
SOUNDS_DIR = 'sounds'

def load_image(name, scale=1):
    fullname = os.path.join(ASSETS_DIR, name)
    try:
        image = pygame.image.load(fullname).convert_alpha() 
        size = image.get_size()
        new_size = (int(size[0] * scale), int(size[1] * scale))
        return pygame.transform.scale(image, new_size)
    except pygame.error as message:
        print(f"Не могу загрузить изображение: {fullname}")
        print("Проверьте наличие файла и правильность пути (папка assets).")
        raise SystemExit(message)

def load_sound(name):
    fullname = os.path.join(SOUNDS_DIR, name)
    try:
        sound = pygame.mixer.Sound(fullname)
        return sound
    except pygame.error as message:
        print(f"Не могу загрузить звук: {fullname}")
        return type('MockSound', (object,), {'play': lambda *args: None, 'set_volume': lambda *args: None})()

try:
    PLAYER_IDLE_IMG = load_image('player_idle.png', scale=PLAYER_SCALE)
    PLAYER_RUN_IMG = load_image('player_run.png', scale=PLAYER_SCALE)
    ENEMY_IMG = load_image('enemy.png', scale=ENEMY_SCALE)
    PLATFORM_IMG = load_image('platform.png', scale=1)
    COIN_IMG = load_image('coin.png', scale=COIN_SCALE)
    BACKGROUND_IMG = load_image('background.png', scale=1)
    BACKGROUND_IMG = pygame.transform.scale(BACKGROUND_IMG, (SCREEN_WIDTH, SCREEN_HEIGHT))
except SystemExit:
    pygame.quit()
    sys.exit()

SOUND_HIT = load_sound('hit.wav')
SOUND_JUMP = load_sound('jump.wav')
SOUND_COIN = load_sound('coin.wav')
SOUND_HIT.set_volume(0.5)
SOUND_COIN.set_volume(0.7)


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = PLAYER_IDLE_IMG
        self.rect = self.image.get_rect(topleft=(x, y))
        self.width = self.rect.width
        self.height = self.rect.height
        
        self.vel_y = 0
        self.dx = 0
        self.in_air = True
        self.facing_right = True

        self.health = 100
        self.score = 0
        self.last_hit_time = 0
        self.invulnerability_duration = 1000  
        self.is_flashing = False
        self.flash_interval = 100 

    def update(self, platform_group):
        self.dx = 0
        
        key = pygame.key.get_pressed()
        
        if key[pygame.K_LEFT]:
            self.dx -= PLAYER_SPEED
            self.facing_right = False
        if key[pygame.K_RIGHT]:
            self.dx += PLAYER_SPEED
            self.facing_right = True

        if (key[pygame.K_SPACE] or key[pygame.K_UP]) and not self.in_air:
            self.vel_y = PLAYER_JUMP_POWER
            self.in_air = True
            SOUND_JUMP.play()

        current_image = PLAYER_RUN_IMG if self.dx != 0 else PLAYER_IDLE_IMG
        
        if not self.facing_right:
            self.image = pygame.transform.flip(current_image, True, False)
        else:
            self.image = current_image

        self.vel_y += GRAVITY
        if self.vel_y > 15:
            self.vel_y = 15
        self.rect.y += int(self.vel_y)

        self.in_air = True
        for platform in platform_group:
            if platform.rect.colliderect(self.rect.x, self.rect.y, self.width, self.height):
                if self.vel_y > 0: 
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.in_air = False
                elif self.vel_y < 0: 
                    self.rect.top = platform.rect.bottom
                    self.vel_y = 0

        self.rect.x += self.dx
        
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

        current_time = pygame.time.get_ticks()
        if current_time < self.last_hit_time + self.invulnerability_duration:
            self.is_flashing = True
            if current_time % (2 * self.flash_interval) < self.flash_interval:
                self.image.set_alpha(0)  
            else:
                self.image.set_alpha(255)  
        else:
            self.is_flashing = False
            self.image.set_alpha(255)  

    def take_damage(self, damage):
        current_time = pygame.time.get_ticks()
        if current_time > self.last_hit_time + self.invulnerability_duration:
            self.health -= damage
            self.last_hit_time = current_time
            SOUND_HIT.play()
            return True
        return False

    def draw(self):
        SCREEN.blit(self.image, self.rect)

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = ENEMY_IMG
        self.rect = self.image.get_rect(topleft=(x, y))
        self.width = self.rect.width
        self.height = self.rect.height
        
        self.vel_y = 0
        self.in_air = True
        self.facing_right = True
        self.speed = ENEMY_SPEED
        self.damage = 10
        
        self.move_direction = 1  
        self.jump_cooldown = 0
        self.jump_delay = 60 

    def update(self, player_rect, platform_group):
        self.vel_y += GRAVITY
        if self.vel_y > 15:
            self.vel_y = 15
        self.rect.y += int(self.vel_y)
        
        self.in_air = True
        
        for platform in platform_group:
            if platform.rect.colliderect(self.rect.x, self.rect.y, self.width, self.height):
                if self.vel_y > 0:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.in_air = False
                elif self.vel_y < 0:
                    self.rect.top = platform.rect.bottom
                    self.vel_y = 0
                    
        if player_rect.centerx > self.rect.centerx:
            self.move_direction = 1
            self.facing_right = True
        else:
            self.move_direction = -1
            self.facing_right = False
        
        self.rect.x += self.move_direction * self.speed
        
        if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
            self.move_direction *= -1
            self.rect.x += self.move_direction * self.speed * 2 
            self.facing_right = not self.facing_right

        if not self.in_air:
            can_jump = False
            
            test_rect = self.rect.copy()
            test_rect.x += self.move_direction * self.speed * 5  
            test_rect.y += 1 
            
            is_on_platform_ahead = any(platform.rect.colliderect(test_rect) for platform in platform_group)
            
            if not is_on_platform_ahead:
                 can_jump = True

            if player_rect.bottom < self.rect.top - 5: 
                if abs(player_rect.centerx - self.rect.centerx) < TILE_SIZE * 5:
                    can_jump = True
            
            if can_jump and self.jump_cooldown <= 0:
                self.jump_cooldown = self.jump_delay
                self.vel_y = ENEMY_JUMP_POWER
                self.in_air = True

        if self.jump_cooldown > 0:
            self.jump_cooldown -= 1
            
        current_image = ENEMY_IMG
        if not self.facing_right:
            self.image = pygame.transform.flip(current_image, True, False)
        else:
            self.image = current_image

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.transform.scale(PLATFORM_IMG, (width, height))
        self.rect = self.image.get_rect(topleft=(x, y))

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = COIN_IMG
        self.rect = self.image.get_rect(center=(x, y))

def create_random_platforms(player_height):
    platforms = pygame.sprite.Group()
    
    floor = Platform(0, SCREEN_HEIGHT - TILE_SIZE, SCREEN_WIDTH, TILE_SIZE)
    platforms.add(floor)
    
    last_platform = floor 
    
    max_platforms = 8
    min_platform_width = TILE_SIZE * 2
    max_platform_width = TILE_SIZE * 4
    
    MIN_Y_SPAWN = TILE_SIZE * 2 

    for i in range(max_platforms):
        
        min_y_limit = MIN_Y_SPAWN
        max_y_limit_by_jump = last_platform.rect.top - (player_height // 2) 

        min_y = max(min_y_limit, last_platform.rect.top - MAX_JUMP_HEIGHT)

        max_y = max_y_limit_by_jump
        
        if min_y >= max_y: 
            y = random.randint(max_y - MAX_JUMP_HEIGHT, max_y - TILE_SIZE)
            y = max(MIN_Y_SPAWN, y) 
        else:
            y = random.randint(min_y, max_y)
            
        width = random.randint(min_platform_width // TILE_SIZE, max_platform_width // TILE_SIZE) * TILE_SIZE
        
        min_x = max(0, last_platform.rect.left - MAX_RUN_DISTANCE) 
        max_x = min(SCREEN_WIDTH - width, last_platform.rect.right + MAX_RUN_DISTANCE - width)
        
        if min_x > max_x: 
            x = last_platform.rect.left + (random.choice([-1, 1]) * TILE_SIZE * 2) 
            x = max(0, min(SCREEN_WIDTH - width, x))
        else:
            x = random.randint(min_x, max_x)

        new_platform = Platform(x, y, width, TILE_SIZE // 2)
        platforms.add(new_platform)
        last_platform = new_platform
              
    return platforms

def spawn_coin(platform_group):
    if not platform_group:
        return None
        
    available_platforms = list(platform_group)[1:] 
    if not available_platforms:
        available_platforms = list(platform_group)

    platform = random.choice(available_platforms)
    x = platform.rect.x + platform.rect.width // 2
    y = platform.rect.y - COIN_IMG.get_height()
    return Coin(x, y)

def draw_text(surface, text, font_size, x, y, color=WHITE):
    font = pygame.font.Font(pygame.font.match_font('arial'), font_size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(topleft=(x, y))
    surface.blit(text_surface, text_rect)

def reset_game(current_health=100, current_score=0): 
    
    platform_group = create_random_platforms(PLAYER_IDLE_IMG.get_height())
    
    floor = [p for p in platform_group if p.rect.y == SCREEN_HEIGHT - TILE_SIZE][0]
    
    player = Player(50, floor.rect.top - PLAYER_IDLE_IMG.get_height())
    
    player.health = current_health 
    player.score = current_score
    
    enemy_group = pygame.sprite.Group()
    enemy_x1 = random.randint(200, SCREEN_WIDTH // 2 - 50)
    enemy_x2 = random.randint(SCREEN_WIDTH // 2 + 50, SCREEN_WIDTH - 200)
    
    enemy_group.add(Enemy(enemy_x1, floor.rect.top - ENEMY_IMG.get_height()))
    enemy_group.add(Enemy(enemy_x2, floor.rect.top - ENEMY_IMG.get_height()))
    
    coin = spawn_coin(platform_group)
    coin_group = pygame.sprite.Group(coin)
    
    return player, platform_group, enemy_group, coin_group

def main():
    clock = pygame.time.Clock()
    game_over = False
    
    global player, platform_group, enemy_group, coin_group
    player, platform_group, enemy_group, coin_group = reset_game()

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if game_over and event.key == pygame.K_SPACE:
                    player, platform_group, enemy_group, coin_group = reset_game()
                    game_over = False
                
        if game_over:
            SCREEN.blit(BACKGROUND_IMG, (0, 0))
            draw_text(SCREEN, "ВЫ ПОГИБЛИ!", 64, SCREEN_WIDTH // 2 - 180, SCREEN_HEIGHT // 3, RED)
            draw_text(SCREEN, f"ФИНАЛЬНЫЙ СЧЕТ: {player.score}", 40, SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 3 + 70, YELLOW)
            draw_text(SCREEN, "Нажмите ПРОБЕЛ для рестарта", 30, SCREEN_WIDTH // 2 - 180, SCREEN_HEIGHT // 3 + 120, WHITE)
            pygame.display.flip()
            continue
        
        player.update(platform_group)
        enemy_group.update(player.rect, platform_group)
        
        for enemy in enemy_group:
            if player.rect.colliderect(enemy.rect):
                player.take_damage(enemy.damage)
                
        if player.health <= 0:
            game_over = True
            
        coin_hit = pygame.sprite.spritecollide(player, coin_group, True)
        if coin_hit:

            score_before_coin = player.score 
            player.score += 10
            SOUND_COIN.play()
            

            if player.score // SCORE_THRESHOLD_FOR_REGEN > score_before_coin // SCORE_THRESHOLD_FOR_REGEN and not game_over:
                
                saved_health = player.health
                saved_score = player.score
                
                player, platform_group, enemy_group, coin_group = reset_game(saved_health, saved_score)
                
                print(f"--- УРОВЕНЬ ПЕРЕГЕНЕРИРОВАН! Счет: {player.score}, Здоровье: {player.health} ---")
                
            else:
                new_coin = spawn_coin(platform_group)
                if new_coin:
                    coin_group.add(new_coin)

        SCREEN.blit(BACKGROUND_IMG, (0, 0))

        platform_group.draw(SCREEN)
        coin_group.draw(SCREEN)
        enemy_group.draw(SCREEN)
        
        player.draw()

        draw_text(SCREEN, f"Здоровье: {player.health}", 24, 10, 10, RED)
        draw_text(SCREEN, f"Счет: {player.score}", 24, 10, 40, YELLOW)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()