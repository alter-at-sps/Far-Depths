#version 420

in vec2 frag_uv;
out vec4 frag;

uniform sampler2D in_frame;

const float distorsion_strenght = .12;

void main() {
    // simulates the distorsion caused by the curve of a CRT monitor

    vec2 dist = .5 - frag_uv;
    
    vec2 dist_uv;
    dist_uv.x = (frag_uv.x - dist.y * dist.y * dist.x * distorsion_strenght /*todo: fit acording to aspect ratio /(iResolution.x/iResolution.y)*/);
    dist_uv.y = (frag_uv.y - dist.x * dist.x * dist.y * distorsion_strenght);

    frag = texture(in_frame, dist_uv);

    // cull pixels "outside" the CRT monitor surface
    frag.xyz *= vec3(((dist_uv.x >= 0.0) && (dist_uv.x <= 1.0)) && ((dist_uv.y >= 0.0) && (dist_uv.y <= 1.0)));
}