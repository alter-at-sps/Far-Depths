#version 330

// based on the PBR bloom implementation done on https://learnopengl.com/Guest-Articles/2022/Phys.-Based-Bloom
// which is based on the Call Of Duty Siggraph 2014 bloom implementation

uniform sampler2D in_texture;
const float filter_radius = .005;

in vec2 frag_uv;
out vec3 frag;

void main() {
    // upsample the downsampled mips using another (3x3 tent) kernel

    float x = filter_radius;
    float y = filter_radius;

    // Take 9 samples around current texel:
    // a - b - c
    // d - e - f
    // g - h - i

    vec3 a = texture(in_texture, vec2(frag_uv.x - x, frag_uv.y + y)).rgb;
    vec3 b = texture(in_texture, vec2(frag_uv.x,     frag_uv.y + y)).rgb;
    vec3 c = texture(in_texture, vec2(frag_uv.x + x, frag_uv.y + y)).rgb;

    vec3 d = texture(in_texture, vec2(frag_uv.x - x, frag_uv.y)).rgb;
    vec3 e = texture(in_texture, vec2(frag_uv.x,     frag_uv.y)).rgb;
    vec3 f = texture(in_texture, vec2(frag_uv.x + x, frag_uv.y)).rgb;

    vec3 g = texture(in_texture, vec2(frag_uv.x - x, frag_uv.y - y)).rgb;
    vec3 h = texture(in_texture, vec2(frag_uv.x,     frag_uv.y - y)).rgb;
    vec3 i = texture(in_texture, vec2(frag_uv.x + x, frag_uv.y - y)).rgb;

    // apply the 3x3 tent kernel weights
    frag = e * 4.;
    frag += (b+d+f+h) * 2.;
    frag += (a+c+g+i);
    frag *= 1. / 16.;
}