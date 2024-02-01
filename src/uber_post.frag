#version 450

in vec4 frag_color;
out vec4 frag;

uniform float time;
uniform sampler2D pygame_fb;

void main() {
    // frag = vec4(1.0f, 0.0f, 1.0f, 1.0f);
    // frag = vec4(frag_color.xy, gl_FragCoord.zw);

    // vec3 col = 0.5 + 0.5*cos(time + vec3(frag_color.xy, gl_FragCoord.z) + vec3(0,2,4));

    frag = texture(pygame_fb, frag_color.xy);
}