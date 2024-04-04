#version 330

// far depths specific bloom shader which overlays the bloom texture over the output fb

uniform sampler2D in_texture;
uniform sampler2D in_bloom_texture;

const float bloom_strength = .008;

in vec2 frag_uv;
out vec3 frag;

void main() {
    // frag = texture(in_texture, frag_uv).xyz;
    // frag = texture(in_bloom_texture, frag_uv).xyz;
    frag = mix(texture(in_texture, frag_uv), texture(in_bloom_texture, frag_uv), bloom_strength).xyz;
}