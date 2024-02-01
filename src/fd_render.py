import pygame as pg
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

class FDContext:
    def __init__(self, res):
        self.win = pg.display.set_mode(res, pg.OPENGL | pg.DOUBLEBUF, vsync=1)
        
        self.create_pg_framebuffer(res)
        self.set_post_process_shader("src/uber_post.vert", "src/uber_post.frag")

    # creates a "shared" pygame opengl texture framebuffer
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

    # load post-processing program
    def set_post_process_shader(self, vert, frag):
        vs = load_shader(gl.GL_VERTEX_SHADER, vert)
        fs = load_shader(gl.GL_FRAGMENT_SHADER, frag)

        p = gl.glCreateProgram()

        gl.glAttachShader(p, vs)
        gl.glAttachShader(p, fs)
    
        gl.glLinkProgram(p)

        result = gl.glGetProgramiv(p, gl.GL_LINK_STATUS)

        if not result:
            log = gl.glGetProgramInfoLog(p)

            print("error while linking a Gl shader program: ", log)
            quit()

        gl.glDeleteShader(vs)
        gl.glDeleteShader(fs)

        self.post_process_pass = p

    def post_process(self):
        # gl.glClearColor(.1, .1, .1, 1)
        # gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        gl.glUseProgram(self.post_process_pass)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.pg_fb_texture)
        # gl.glUniform1f(time_loc, time_)
    
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)

# == init the renderer ==

fd_renderer = FDContext((1280, 720))

# == renderer api ==

# get surface that pygame draws to
def get_surface():
    return fd_renderer.pg_fb

# flags that pygame pass is finished, starting post-processing pass
def submit():
    fd_renderer.flip_pg_framebuffer()

    # post-processing pass

    fd_renderer.post_process()

    # frame finished

    pg.display.flip() # flips the window (opengl) surface