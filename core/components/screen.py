import pygame
import numpy as np
import threading

class Screen:
    def __init__(self, memory, scale=4):
        """initialize the screen with a memory object and scale."""
        self.memory = memory
        self.scale = scale
        self.width = 128
        self.height = 128
        # screen memory address and size from Memory object
        self.screen_ram_start = memory.SCREEN_RAM_START
        self.screen_ram_size = self.width * self.height  # 16384 bytes
        pygame.init()
        self.window = pygame.display.set_mode((self.width * self.scale, self.height * self.scale))
        pygame.display.set_caption("6502 Emulator Screen")
        self.clock = pygame.time.Clock()
        self.running = True
        self.thread = None   # added thread handle

    def draw(self):
        """render the current video memory contents with palette mapping."""
        # Read and reshape the screen memory (8-bit per pixel)
        screen_data = np.frombuffer(
            self.memory.data[self.screen_ram_start : self.screen_ram_start + self.screen_ram_size],
            dtype=np.uint8
        ).reshape((self.height, self.width))
        # Default: create a grayscale image by replicating the 8-bit value over R, G, B
        rgb_array = np.stack([screen_data, screen_data, screen_data], axis=-1)
        # Palette override: if a pixel equals $E0, display it as red (255,0,0)
        red_mask = (screen_data == 0xE0)
        rgb_array[red_mask] = [255, 0, 0]
        surface = pygame.surfarray.make_surface(rgb_array)
        scaled_surface = pygame.transform.scale(surface, (self.width * self.scale, self.height * self.scale))
        self.window.blit(scaled_surface, (0, 0))
        pygame.display.flip()

    def run(self):
        """Asynchronous update loop running on a separate thread."""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            self.draw()
            self.clock.tick(120)

    def start(self):
        """start the screen update thread."""
        self.thread = threading.Thread(target=self.run, daemon=False)  # daemon set to False
        self.thread.start()

    def stop(self):
        """stop the screen thread and join it."""
        self.running = False
        if self.thread:
            self.thread.join()