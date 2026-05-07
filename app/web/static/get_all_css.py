import os

def collect_css_files(base_dir):
    css_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".css"):
                full_path = os.path.join(root, file)
                css_files.append(full_path)
    return css_files


def write_combined_css(css_files, output_file):
    with open(output_file, "w", encoding="utf-8") as outfile:
        for css_file in css_files:
            try:
                with open(css_file, "r", encoding="utf-8") as infile:
                    outfile.write(f"\n/* ===== {css_file} ===== */\n\n")
                    outfile.write(infile.read())
                    outfile.write("\n")
            except Exception as e:
                print(f"Error reading {css_file}: {e}")


if __name__ == "__main__":
    current_dir = os.getcwd()
    output_path = os.path.abspath(os.path.join(current_dir, "../all_css.css"))

    css_files = collect_css_files(current_dir)
    write_combined_css(css_files, output_path)

    print(f"Combined {len(css_files)} CSS files into: {output_path}")