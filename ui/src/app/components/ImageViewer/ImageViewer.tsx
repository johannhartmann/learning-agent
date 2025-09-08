"use client";

import React from "react";
import Image from "next/image";
import styles from "./ImageViewer.module.scss";

export interface ImageData {
  type: "matplotlib" | "pil" | "other";
  format: "png" | "jpeg";
  base64: string;
}

interface ImageViewerProps {
  images: ImageData[];
  className?: string;
}

export const ImageViewer: React.FC<ImageViewerProps> = ({ images, className = "" }) => {
  if (!images || images.length === 0) {
    return null;
  }

  return (
    <div className={`${styles.container} ${className}`}>
      {images.map((img, idx) => (
        <div key={idx} className={styles.imageWrapper}>
          <Image
            src={`data:image/${img.format};base64,${img.base64}`}
            alt={`Figure ${idx + 1}`}
            className={styles.image}
            width={800}
            height={600}
            unoptimized
          />
          <p className={styles.caption}>Figure {idx + 1}</p>
        </div>
      ))}
    </div>
  );
};

ImageViewer.displayName = "ImageViewer";
