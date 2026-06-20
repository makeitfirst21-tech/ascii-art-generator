import sys

COLORS = {
    "red":     "\033[91m",
    "green":   "\033[92m",
    "yellow":  "\033[93m",
    "blue":    "\033[94m",
    "magenta": "\033[95m",
    "cyan":    "\033[96m",
    "white":   "\033[97m",
    "reset":   "\033[0m",
}

# 5-row tall block font, each char is a list of 5 strings (width varies)
FONT = {
    'A': ["  #  ", " # # ", "#####", "#   #", "#   #"],
    'B': ["#### ", "#   #", "#### ", "#   #", "#### "],
    'C': [" ####", "#    ", "#    ", "#    ", " ####"],
    'D': ["#### ", "#   #", "#   #", "#   #", "#### "],
    'E': ["#####", "#    ", "###  ", "#    ", "#####"],
    'F': ["#####", "#    ", "###  ", "#    ", "#    "],
    'G': [" ####", "#    ", "# ###", "#   #", " ####"],
    'H': ["#   #", "#   #", "#####", "#   #", "#   #"],
    'I': ["#####", "  #  ", "  #  ", "  #  ", "#####"],
    'J': ["#####", "   # ", "   # ", "#  # ", " ##  "],
    'K': ["#   #", "#  # ", "###  ", "#  # ", "#   #"],
    'L': ["#    ", "#    ", "#    ", "#    ", "#####"],
    'M': ["#   #", "## ##", "# # #", "#   #", "#   #"],
    'N': ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    'O': [" ### ", "#   #", "#   #", "#   #", " ### "],
    'P': ["#### ", "#   #", "#### ", "#    ", "#    "],
    'Q': [" ### ", "#   #", "# # #", "#  # ", " ## #"],
    'R': ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    'S': [" ####", "#    ", " ### ", "    #", "#### "],
    'T': ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    'U': ["#   #", "#   #", "#   #", "#   #", " ### "],
    'V': ["#   #", "#   #", "#   #", " # # ", "  #  "],
    'W': ["#   #", "#   #", "# # #", "## ##", "#   #"],
    'X': ["#   #", " # # ", "  #  ", " # # ", "#   #"],
    'Y': ["#   #", " # # ", "  #  ", "  #  ", "  #  "],
    'Z': ["#####", "   # ", "  #  ", " #   ", "#####"],
    '0': [" ### ", "#  ##", "# # #", "##  #", " ### "],
    '1': [" ## ", "# # ", "  # ", "  # ", "#####"],
    '2': [" ### ", "#   #", "  ## ", " #   ", "#####"],
    '3': ["#### ", "    #", " ### ", "    #", "#### "],
    '4': ["#  # ", "#  # ", "#####", "   # ", "   # "],
    '5': ["#####", "#    ", "#### ", "    #", "#### "],
    '6': [" ### ", "#    ", "#### ", "#   #", " ### "],
    '7': ["#####", "    #", "   # ", "  #  ", " #   "],
    '8': [" ### ", "#   #", " ### ", "#   #", " ### "],
    '9': [" ### ", "#   #", " ####", "    #", " ### "],
    '!': [" # ", " # ", " # ", "   ", " # "],
    '?': [" ### ", "#   #", "  ## ", "     ", "  #  "],
    ' ': ["   ", "   ", "   ", "   ", "   "],
    '.': ["  ", "  ", "  ", "  ", " #"],
    '-': ["   ", "   ", "###", "   ", "   "],
    '+': ["   ", " # ", "###", " # ", "   "],
}

STYLES = {
    "block":   ("#", "#", "#"),
    "bold":    ("█", "█", "█"),
    "shadow":  ("▓", "░", "▒"),
    "dots":    ("●", "●", "●"),
    "retro":   ("▮", "▮", "▮"),
}

def render(text, style="block", color="white"):
    chars = text.upper()
    fill, _, _ = STYLES.get(style, STYLES["block"])
    color_code = COLORS.get(color, COLORS["white"])
    reset = COLORS["reset"]

    rows = [""] * 5
    for ch in chars:
        pattern = FONT.get(ch, FONT[' '])
        for i, row in enumerate(pattern):
            rows[i] += row.replace("#", fill) + "  "

    print()
    for row in rows:
        print(color_code + row + reset)
    print()
    return rows

def pick(prompt, options):
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        choice = input("  > ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        if choice.lower() in [o.lower() for o in options]:
            return choice.lower()
        print("  Pick a number from the list.")

def main():
    print("\033[96m" + "=" * 50)
    print("  ASCII ART GENERATOR")
    print("=" * 50 + "\033[0m")

    while True:
        text = input("\nEnter text (or 'q' to quit): ").strip()
        if text.lower() == 'q':
            print("Bye!\n")
            break
        if not text:
            continue

        style = pick("Choose a style:", list(STYLES.keys()))
        color = pick("Choose a color:", [c for c in COLORS if c != "reset"])

        rows = render(text, style, color)

        save = input("Save to file? (y/n): ").strip().lower()
        if save == 'y':
            filename = f"{''.join(c for c in text if c.isalnum() or c == ' ').strip().replace(' ', '_')}_{style}.txt"
            filepath = f"C:\\Users\\makei\\Documents\\ascii-art-generator\\{filename}"
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Text: {text}  |  Style: {style}  |  Color: {color}\n\n")
                f.write("\n".join(rows) + "\n")
            print(f"  Saved to {filename}")

        again = input("Make another? (y/n): ").strip().lower()
        if again != 'y':
            print("Bye!\n")
            break

if __name__ == "__main__":
    main()
