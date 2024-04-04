#version 330

in vec2 frag_uv;
out vec4 frag;

uniform sampler2D in_frame;
uniform float time;

const float aberration_strength = 0.12;

const float scanline_count = 800;
const float scanline_strenght = 0.04;

void main() {
    // Chromatic aberration

    vec2 ab_offset = vec2(0.01 * aberration_strength, 0.0);

    vec3 col;
    col.x = texture(in_frame, frag_uv + ab_offset).x;
    col.y = texture(in_frame, frag_uv).y;
    col.z = texture(in_frame, frag_uv - ab_offset).z;

    // scanlines

    float scanline_luminisence = sin(frag_uv.y * scanline_count) * scanline_strenght;
    col -= scanline_luminisence / 2;

    frag = vec4(col, 1.0);
}