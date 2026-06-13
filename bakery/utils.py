import random

def generate_captcha_svg(code):
    """
    Generates a raw XML/SVG string containing CAPTCHA text.
    Uses lines and circles for noise, along with randomized fonts,
    sizes, and rotation angles to make simple OCR difficult.
    """
    width = 140
    height = 45
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="100%" height="100%" fill="#f3f4f6" rx="5" ry="5" stroke="#d1d5db" stroke-width="1"/>'
    ]
    
    # Grid of noise points or lines
    colors = ["#cbd5e1", "#94a3b8", "#cbd5e1", "#e2e8f0"]
    for _ in range(4):
        x1 = random.randint(0, 40)
        y1 = random.randint(0, height)
        x2 = random.randint(width - 40, width)
        y2 = random.randint(0, height)
        color = random.choice(colors)
        stroke_w = random.uniform(1.0, 2.0)
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{stroke_w}" />')
        
    for _ in range(15):
        cx = random.randint(0, width)
        cy = random.randint(0, height)
        r = random.randint(1, 3)
        color = random.choice(colors)
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity="0.7"/>')
        
    # Render letters with random rotations, fonts, and vertical shifts
    char_width = (width - 20) / len(code)
    font_families = ["Courier New", "monospace", "Georgia", "Arial"]
    for i, char in enumerate(code):
        x = 12 + (i * char_width) + random.randint(-3, 3)
        y = 30 + random.randint(-4, 4)
        angle = random.randint(-20, 20)
        font = random.choice(font_families)
        size = random.randint(22, 26)
        color = random.choice(["#1e293b", "#0f172a", "#334155", "#475569"])
        svg.append(
            f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="bold" '
            f'fill="{color}" transform="rotate({angle}, {x}, {y})">{char}</text>'
        )
        
    svg.append('</svg>')
    return "\n".join(svg)
