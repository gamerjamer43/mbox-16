import pygame, numpy as np, threading

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

        # initialize pygame and create a window, and ticker for frame rate control
        pygame.init()
        self.window = pygame.display.set_mode((self.width * self.scale, self.height * self.scale))
        pygame.display.set_caption("6502 Emulator Screen")
        self.clock = pygame.time.Clock()

        # running state and thread handle
        self.running = True
        self.thread = None

    def draw(self):
        """render the current video memory contents using 8-bit (3-3-2) palette mapping."""
        # read and reshape the screen memory (8-bit per pixel)
        screen_data = np.frombuffer(
            self.memory.data[self.screen_ram_start : self.screen_ram_start + self.screen_ram_size],
            dtype=np.uint8
        ).reshape((self.height, self.width))

        # build 8-bit palette using a 3-3-2 bit mapping
        palette = np.empty((256, 3), dtype=np.uint8)
        for i in range(256):
            r = (i >> 5) & 0x07  # red: 0-7
            g = (i >> 2) & 0x07  # green: 0-7
            b = i & 0x03         # blue: 0-3
            palette[i] = [int(r * 255 / 7), int(g * 255 / 7), int(b * 255 / 3)]

        # map each pixel to its corresponding RGB color using the palette, blit to surface
        rgb_array = palette[screen_data]
        surface = pygame.surfarray.make_surface(rgb_array)
        scaled_surface = pygame.transform.scale(surface, (self.width * self.scale, self.height * self.scale))
        self.window.blit(scaled_surface, (0, 0))
        pygame.display.flip()

    def run(self):
        """asynchronous update loop running on a separate thread."""
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