"""
This script contains functions used in the context where TCPs are deployed.
"""
import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from skimage import filters
from skimage.segmentation import flood


def regconv(r, t):
    c = cv.filter2D(r, ddepth=cv.CV_32F, kernel=t, borderType=cv.BORDER_CONSTANT)
    m, n = np.where(c == c.max())
    m, n = int(m[0]-t.shape[0]/2), int(n[0]-t.shape[1]/2)  
    h = np.stack((r,), axis=-1)    
    return h[m:m+t.shape[0], n:n+t.shape[1]], m, n

def find_tcp(img_path, ref_tcp_path):
    img = cv.imread(img_path, cv.IMREAD_GRAYSCALE)
    ref_tcp = cv.imread(ref_tcp_path, cv.IMREAD_GRAYSCALE)
    #img = cv.gaussia
    res, m, n = regconv(img, ref_tcp)
    thresh = filters.threshold_otsu(res)
    binary = res > thresh
    mid = (res.shape[0]//2, res.shape[1]//2)
    mask = flood(binary[:,:,0], mid, connectivity=1)

    kernel = np.ones((7, 7), np.uint8)
    erosion = cv.erode(mask.astype(float), kernel, iterations=1)
    #print("N. of pixels detected:", erosion.sum())
    if erosion.sum() < 85:
        return None, None, None, None, None
    
    cx, cy = m+erosion.shape[0]//2, n+erosion.shape[1]//2

    return erosion, m, n, cx, cy

def extract_plate_temperature(temp_img, cx, cy, radius=5):
    patch = temp_img[cx-radius:cx+radius, cy-radius:cy+radius]
    #patch_corrected_T = patch(patch, 0.985, 23)
    return np.median(patch)

def finding_dory(temp_img, cx, cy, vector, radius=5):
    def finding_nemo(dvx,dvy):
        patch = temp_img[cx - radius + dvx: cx + radius + dvx, cy - radius + dvy: cy+radius + dvy]
        #patch_corrected_T = correct_brightness_to_lst(patch, 0.99, 23)
        return np.mean(patch), np.median(patch)
    
    vx, vy = vector
    mean_fwd, med_fwd = finding_nemo(vx, vy)
    mean_bwd, med_bwd = finding_nemo(-vx, -vy)
    if mean_fwd <= mean_bwd:
        return med_fwd, np.array([vx, vy])
    else:
        return med_bwd, np.array([-vx, -vy])

def plot_detected_tcp(img, erosion, m, n, cx, cy, water_vector=None, radius=5, title="", ax=None):
    created_fig = ax is None
    if created_fig:
        fig, ax = plt.subplots(figsize=(10, 7))
    else:
        fig = ax.figure

    big_mask = np.zeros(img.shape, dtype=np.float32)
    big_mask[m:m+erosion.shape[0], n:n+erosion.shape[1]] = erosion
    ax.imshow(img, cmap="inferno")
    ax.imshow(big_mask, alpha=0.4)

    handles = []
    plate_rect = mpatches.Rectangle((cy - radius, cx - radius), 2 * radius, 2 * radius, edgecolor='red', facecolor='none', linewidth=2)
    ax.add_patch(plate_rect)
    handles.append(mpatches.Patch(edgecolor='red', facecolor='none', label='Detected TCP'))

    if water_vector is not None:
        vx, vy = int(water_vector[0]), int(water_vector[1])
        wx, wy = cx + vx, cy + vy
        water_rect = mpatches.Rectangle((wy - radius, wx - radius), 2 * radius, 2 * radius, edgecolor='cyan', facecolor='none', linewidth=2)
        ax.add_patch(water_rect)
        handles.append(mpatches.Patch(edgecolor='cyan', facecolor='none', label='Water temperature extraction'))

    ax.set_title(title, fontsize=12)
    ax.legend(handles=handles, loc='lower right', framealpha=0.9)
    ax.axis('off')
    if created_fig:
        plt.tight_layout()
    return fig

def plot_template_match(img, ref_gray, erosion, m, n, cx, cy, water_vector=None, radius=5, title=""):
    tie_c = "#ff3b30"
    box_c = "#ff3b30"
    eh, ew = erosion.shape[:2]
    fig, (ax_ref, ax_img) = plt.subplots(
        1, 2, figsize=(12, 6),
        gridspec_kw={"width_ratios": [1, 2.4]})

    ax_ref.imshow(ref_gray, cmap="inferno")
    ax_ref.set_title("Reference template", fontsize=11)
    ax_ref.axis("off")
    for s in ax_ref.spines.values():
        s.set_visible(True); s.set_edgecolor(box_c); s.set_linewidth(2.5)

    plot_detected_tcp(img, erosion, m, n, cx, cy,
                      water_vector=water_vector, radius=radius,
                      title="Image", ax=ax_img)

    ax_img.add_patch(mpatches.Rectangle((n, m), ew, eh, fill=False,
                                        edgecolor=box_c, lw=1.5, ls=":"))

    rh, rw = ref_gray.shape[:2]
    for (rx, ry), (ix, iy) in [((-0.5, -0.5), (n, m)),
                               ((rw - 0.5, rh - 0.5), (n + ew, m + eh))]:
        fig.add_artist(mpatches.ConnectionPatch(
            xyA=(rx, ry), coordsA=ax_ref.transData,
            xyB=(ix, iy), coordsB=ax_img.transData,
            color=tie_c, lw=1.3, ls="--", alpha=0.9))

    if title:
        fig.suptitle(title, fontsize=13)
    fig.tight_layout()
    return fig

def plate_stats(timg, erosion, m, n):
    mask = np.zeros(timg.shape, dtype=bool)
    mask[m:m+erosion.shape[0], n:n+erosion.shape[1]] = erosion.astype(bool)
    surf = timg[mask]; surf = surf[np.isfinite(surf)]
    if surf.size == 0:
        return np.nan, np.nan, 0
    return float(np.median(surf)), float(np.std(surf)), int(surf.size)

def water_stats(timg, cx, cy, vector, radius=5):
    vx, vy = int(vector[0]), int(vector[1])
    p = timg[cx-radius+vx:cx+radius+vx, cy-radius+vy:cy+radius+vy]; p = p[np.isfinite(p)]
    if p.size == 0:
        return np.nan, np.nan, 0
    return float(np.median(p)), float(np.std(p)), int(p.size)