#version 420

// based on the PBR bloom implementation done on https://learnopengl.com/Guest-Articles/2022/Phys.-Based-Bloom
// which is based on the Call Of Duty Siggraph 2014 bloom implementation

uniform sampler2D in_texture;
uniform ivec2 in_res;

in vec2 frag_uv;
out vec3 downsampled_frag;

const float intensity = 2;

void main() {
    vec2 texel_size = 1. / in_res;
    float x = texel_size.x;
    float y = texel_size.y;

    // sample using the Call Of Duty kernel with their respective weights

    // Take 13 samples around current texel:
    // a - b - c
    // - j - k -
    // d - e - f
    // - l - m -
    // g - h - i

    vec3 a = texture(in_texture, vec2(frag_uv.x - 2*x, frag_uv.y + 2*y)).rgb;
    vec3 b = texture(in_texture, vec2(frag_uv.x,       frag_uv.y + 2*y)).rgb;
    vec3 c = texture(in_texture, vec2(frag_uv.x + 2*x, frag_uv.y + 2*y)).rgb;

    vec3 d = texture(in_texture, vec2(frag_uv.x - 2*x, frag_uv.y)).rgb;
    vec3 e = texture(in_texture, vec2(frag_uv.x,       frag_uv.y)).rgb;
    vec3 f = texture(in_texture, vec2(frag_uv.x + 2*x, frag_uv.y)).rgb;

    vec3 g = texture(in_texture, vec2(frag_uv.x - 2*x, frag_uv.y - 2*y)).rgb;
    vec3 h = texture(in_texture, vec2(frag_uv.x,       frag_uv.y - 2*y)).rgb;
    vec3 i = texture(in_texture, vec2(frag_uv.x + 2*x, frag_uv.y - 2*y)).rgb;

    vec3 j = texture(in_texture, vec2(frag_uv.x - x, frag_uv.y + y)).rgb;
    vec3 k = texture(in_texture, vec2(frag_uv.x + x, frag_uv.y + y)).rgb;
    vec3 l = texture(in_texture, vec2(frag_uv.x - x, frag_uv.y - y)).rgb;
    vec3 m = texture(in_texture, vec2(frag_uv.x + x, frag_uv.y - y)).rgb;

    downsampled_frag = e * intensity * .125;
    downsampled_frag += (a+c+g+i) * intensity * .03125;
    downsampled_frag += (b+d+f+h) * intensity * .0625;
    downsampled_frag += (j+k+l+m) * intensity * .125;
}