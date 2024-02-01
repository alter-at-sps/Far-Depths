#version 450

// full screen triangle
vec4 verts[] = {
    vec4(-1, -1, 0, 1),
    vec4(-1, 5, 0, 1),
    vec4(5, -1, 0, 1),
};

out vec4 frag_color;

void main() {
    frag_color = verts[gl_VertexID % 3];
    gl_Position = verts[gl_VertexID % 3];
}