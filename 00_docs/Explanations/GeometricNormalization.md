# Stage 1 Pipeline Documentation: Geometric Normalization (Deskewing)

**Objective:** To dynamically calculate and correct the rotational skew of scanned archival sheets and field photographs prior to data extraction. This operation ensures that horizontal stratigraphic layers and drawn grid lines align with the pixel grid, minimizing spatial distortion in subsequent boundary detection.

This routine is conditionally executed via the `deskew_flag` parameter and relies on a sequence of computer vision algorithms provided by OpenCV.

---

## Algorithm Overview

When a document is scanned slightly off-axis, the resulting matrix introduces a global rotational error. The pipeline corrects this by isolating straight lines within the image, analyzing their angles to find the dominant horizontal baseline, and applying an inverse rotation to the entire matrix to flatten the image.

If the image contains no detectable horizontal lines, the system safely bypasses the rotation to avoid introducing artificial distortion.

---

## Step-by-Step Mathematical Operations

### 1. Canny Edge Detection

Before lines can be mathematically identified, the image matrix must be reduced to its structural boundaries. The pipeline first applies a Canny edge detector to the grayscale image. This algorithm computes the intensity gradient of the image and suppresses non-maximum pixels, returning a binary matrix where only sharp edges remain active.

### 2. Hough Line Transform

With the edges isolated, the pipeline utilizes the `cv2.HoughLines` algorithm to detect linear structures. The algorithm operates with an accumulator threshold of 200, strictly isolating the first 200 prominent straight lines.

The standard Cartesian equation for a line ($y = mx + b$) fails for vertical lines because the slope $m$ approaches infinity. To solve this, the Hough transform maps the image space $(x, y)$ into a polar parameter space $(\rho, \theta)$ using the following equation:

$$\rho = x\cos(\theta) + y\sin(\theta)$$

Where:

* $\rho$ is the perpendicular distance from the origin to the line.
* $\theta$ is the angle formed by this perpendicular line and the horizontal axis.

Every edge pixel in the image "votes" for the $(\rho, \theta)$ pairs that could pass through it. The local maxima in this accumulator space represent the most dominant continuous lines in the drawing.

### 3. Angle Filtering

Because archaeological drawings contain both horizontal and vertical grid lines, as well as angled layer boundaries, the raw Hough output contains excessive noise. To find the true rotational skew of the paper, the pipeline focuses exclusively on the horizontal baseline.

The pipeline processes the $\theta$ values to determine how many degrees each line is offset from horizontal. It then applies a strict threshold filter, retaining only the lines that fall within a $\pm 15^\circ$ tolerance of a perfect horizontal axis.

### 4. Skew Estimation (Median Calculation)

To determine the final angle of rotation, the pipeline must aggregate the surviving horizontal lines into a single scalar value.

Crucially, the pipeline calculates the **median** angle of these lines rather than the mean. The mathematical median is inherently robust against extreme outliers; this intentional design choice ensures that a handful of near-vertical lines or steep stratigraphic boundaries that slip through the filter do not artificially drag the estimated skew angle.

> **Fallback Condition:** If no lines survive the $\pm 15^\circ$ tolerance filter, the calculated skew is reported as $0.0$, and the image matrix passes through the remainder of the stage unrotated.
> 
> 

### 5. Affine Transformation

Once the median skew angle ($\theta_{\text{skew}}$) is identified, the pipeline flattens the image by applying a single `cv2.warpAffine` rotation.

To prevent the image from shifting off-canvas, the rotation is executed exactly around the image center $(c_x, c_y)$. The 2D affine rotation matrix $R$ is constructed as:

$$R = \begin{bmatrix} \cos(\theta_{\text{skew}}) & -\sin(\theta_{\text{skew}}) & c_x(1 - \cos(\theta_{\text{skew}})) + c_y\sin(\theta_{\text{skew}}) \\ \sin(\theta_{\text{skew}}) & \cos(\theta_{\text{skew}}) & c_y(1 - \cos(\theta_{\text{skew}})) - c_x\sin(\theta_{\text{skew}}) \end{bmatrix}$$

This transformation matrix is multiplied against every pixel coordinate in the image. To maintain image fidelity during this sub-pixel spatial shift, the pipeline employs **cubic interpolation**. Furthermore, to prevent black voids from appearing in the corners of the rotated matrix, the pipeline uses **edge-replicated borders**, extending the outermost pixels to fill the resulting empty space.