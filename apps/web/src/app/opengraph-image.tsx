import { ImageResponse } from "next/og";

export const alt = "The Big Learn — classical Chinese, line by line";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#fafaf9",
        color: "#292524",
        fontFamily: "serif",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 42 }}>
        <div
          style={{
            width: 150,
            height: 150,
            borderRadius: 18,
            background: "#b45309",
            color: "white",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 62,
            lineHeight: 0.9,
          }}
        >
          <span>大</span><span>学</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontSize: 72, fontWeight: 700 }}>The Big Learn</div>
          <div style={{ fontSize: 32, color: "#78716c" }}>Classical Chinese, line by line.</div>
        </div>
      </div>
    </div>,
    size,
  );
}
