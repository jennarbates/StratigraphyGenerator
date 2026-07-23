import cv2
import numpy as np
import matplotlib.pyplot as plt
import sys

def generate_deskew_debug_graphics(input_path, output_path):
    # 1. Load the original image matrix in grayscale
    img = cv2.imread(input_path)
    if img is None:
        print(f"Error: Could not load image at {input_path}")
        return
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Extract Structural Boundaries
    # Apply Canny edge detection to isolate sharp intensity gradients
    edges = cv2.Canny(gray, 50, 150)
    
    # 3. Detect Linear Structures
    # Use the same parameters as the preprocessing pipeline
    lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
    
    # 4. Map the Math to the Image
    debug_img = img.copy()
    if lines is not None:
        # Isolate the first 200 prominent straight lines
        for line in lines[:200]: 
            rho, theta = line[0]
            
            # Convert radians to degrees and calculate offset from perfect horizontal (90 degrees)
            angle_off_horizontal = abs((theta * 180 / np.pi) - 90)
            
            # Retain only lines oriented within +/- 15 degrees of horizontal
            if angle_off_horizontal <= 15:
                # Convert the polar (rho, theta) parameters into Cartesian (x, y) coordinates
                a = np.cos(theta)
                b = np.sin(theta)
                x0 = a * rho
                y0 = b * rho
                
                # Extend the line out by 3000 pixels in both directions to span the image
                x1 = int(x0 + 3000 * (-b))
                y1 = int(y0 + 3000 * (a))
                x2 = int(x0 - 3000 * (-b))
                y2 = int(y0 - 3000 * (a))
                
                # Draw the surviving horizontal lines in pure red (BGR: 0, 0, 255)
                cv2.line(debug_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                
    # 5. Render the Multi-Panel Graphic
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Panel 1: Original Input (Convert BGR to RGB for accurate Matplotlib coloring)
    axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    axes[0].set_title('1. Original Input Image', fontsize=14, pad=10)
    
    # Panel 2: The Binary Canny Edge Matrix
    axes[1].imshow(edges, cmap='gray')
    axes[1].set_title('2. Canny Edge Detection', fontsize=14, pad=10)
    
    # Panel 3: Filtered Hough Lines
    axes[2].imshow(cv2.cvtColor(debug_img, cv2.COLOR_BGR2RGB))
    axes[2].set_title('3. Horizontal Hough Lines (±15°)', fontsize=14, pad=10)
    
    # Remove axis ticks for a clean documentation graphic
    for ax in axes:
        ax.axis('off')
        
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Success! Deskew documentation graphic saved to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_deskew_graphics.py <input_image_path> <output_image_path>")
    else:
        generate_deskew_debug_graphics(sys.argv[1], sys.argv[2])