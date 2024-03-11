import pygame as pg
import pygame.freetype as freetype
import OpenGL.GL as gl

# == Far Depths renderer ==
# a OpenGL / PyGame hybrid abomination

def load_shader(shader_type, path):
    src = open(path, "r")

    s = gl.glCreateShader(shader_type)

    gl.glShaderSource(s, src.read())
    gl.glCompileShader(s)

    result = gl.glGetShaderiv(s, gl.GL_COMPILE_STATUS)

    if not result:
        log = gl.glGetShaderInfoLog(s)

        print("error while compiling a Gl shader: ", log)
        quit()

    return s

class FDRenderer:
    def __init__(self, res):
        self.res = res

        pg.init()

        # disable depricated legacy immediate mode
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        self.win = pg.display.set_mode(res, pg.OPENGL | pg.DOUBLEBUF | pg.RESIZABLE, vsync=1)
        
        self.create_pg_framebuffer()
        self.create_offscreen_framebuffers()
        self.render_passes = []

    # creates a "shared" pygame opengl texture framebuffer
    def create_pg_framebuffer(self):
        self.pg_fb = pg.Surface(self.res)
        self.pg_fb_texture = gl.glGenTextures(1)

        # setup fb texture
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.pg_fb_texture)

        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        # unbind
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    # flags pygames framebuffer as finished and forwards it to opengl
    def flip_pg_framebuffer(self):
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.pg_fb_texture)

        rgba_surface = pg.image.tostring(pg.transform.flip(self.pg_fb, False, True), 'RGBA')

        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, self.res[0], self.res[1], 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, rgba_surface)

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        self.pg_fb.fill((0, 0, 0)) # clear pygame side framebuffer

    def create_offscreen_framebuffers(self):
        self.fbs = gl.glGenFramebuffers(2)
        self.fb_attachments = gl.glGenTextures(2)

        # setup textures that backup the framebuffers
        for attach in self.fb_attachments:
            gl.glBindTexture(gl.GL_TEXTURE_2D, attach)

            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, self.res[0], self.res[1], 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, None)

            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        
        # bind textures to frambuffers as attachments to be used for rendering
        for i in range(2):
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbs[i])

            gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, self.fb_attachments[i], 0)

            if not gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER) == gl.GL_FRAMEBUFFER_COMPLETE:
                print("fd renderer: failed to init offscreen framebuffers!")
                quit()

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    def post_process(self):
        # gl.glClearColor(.1, .1, .1, 1)
        # gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        for i, rpass in enumerate(self.render_passes):
            in_tex = self.fb_attachments[(i - 1) % 2]
            out_fb = self.fbs[i % 2]

            # first pass reads from pygame fb
            if i == 0:
                in_tex = self.pg_fb_texture

            # last pass renders to window framebuffer
            if i == len(self.render_passes) - 1:
                out_fb = 0

            # call renderer implementation (usually in fd_render_lib.py)
            rpass["frame"](rpass, in_tex, out_fb)

# == init the renderer ==

fd_renderer = FDRenderer((1280, 720))

# == renderer api ==

# get surface that pygame draws to
def get_surface():
    return fd_renderer.pg_fb

# resets the current post-processing passes (eg. for changing post-processing profiles)
def reset_passes():
    for rpass in fd_renderer.render_passes:
        cleanup = rpass.get("cleanup")

        if not cleanup == None:
            cleanup(rpass)

    fd_renderer.render_passes.clear()

def add_pass(rpass):
    fd_renderer.render_passes.append(rpass)

# call this when the rendering window is resized
def recreate_renderer(res, upscale):
    # clean up outdated framebuffers
    gl.glDeleteFramebuffers(2, fd_renderer.fbs)
    gl.glDeleteTextures(2, fd_renderer.fb_attachments)

    gl.glDeleteTextures(1, fd_renderer.pg_fb_texture)

    # recreate framebuffers
    fd_renderer.res = (res[0] // upscale, res[1] // upscale)

    fd_renderer.create_pg_framebuffer()
    fd_renderer.create_offscreen_framebuffers()

# flags that pygame pass is finished, starting post-processing pass
def submit():
    fd_renderer.flip_pg_framebuffer()

    # post-processing pass

    fd_renderer.post_process()

    # frame finished

    pg.display.flip() # flips the window (opengl) surface