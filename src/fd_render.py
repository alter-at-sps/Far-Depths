import pygame as pg
import OpenGL.GL as gl

# == Far Depths renderer ==
# a OpenGL / PyGame hybrid abomination

class FDContext:
    def __init__(self, res):
        self.win = pg.display.set_mode(res, pg.OPENGL | pg.DOUBLEBUF, vsync=1)
        
        self.create_pg_framebuffer(res)

    # creates a opengl rgba texture that can store the pygame surface
    def create_pg_framebuffer(self, res):
        self.pg_fb = pg.Surface(res)
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

        rgba_surface = pg.image.tostring(self.pg_fb, 'RGBA')
        width, height = self.pg_fb.get_size()

        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, rgba_surface)

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

# == init the renderer ==

fd_renderer = FDContext((1280, 720))

# == renderer api ==

# get surface that pygame draws to
def get_surface():
    return fd_renderer.pg_fb

# flags that pygame pass is finished, starting post-processing pass
def submit():
    fd_renderer.flip_pg_framebuffer()

    # post-process

    pg.display.flip() # flips the window (opengl) surface