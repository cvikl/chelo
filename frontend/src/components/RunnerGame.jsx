import { useEffect, useRef, useState } from "react";

const CANVAS_W = 700;
const CANVAS_H = 180;
const GROUND_Y = 145;
const GRAVITY = 0.6;
const JUMP_FORCE = -11;
const GAME_SPEED_INIT = 4;

// Simple pixel character (Greta with braids)
function drawGreta(ctx, x, y, frame) {
  ctx.save();

  // Body
  ctx.fillStyle = "#f59e0b"; // yellow jacket
  ctx.fillRect(x + 4, y + 14, 14, 16);

  // Head
  ctx.fillStyle = "#fcd34d";
  ctx.fillRect(x + 6, y + 2, 10, 12);

  // Hair / braids
  ctx.fillStyle = "#92400e";
  ctx.fillRect(x + 5, y + 0, 12, 6);
  ctx.fillRect(x + 4, y + 6, 3, 14); // left braid
  ctx.fillRect(x + 15, y + 6, 3, 14); // right braid

  // Eyes
  ctx.fillStyle = "#1e293b";
  ctx.fillRect(x + 8, y + 6, 2, 2);
  ctx.fillRect(x + 12, y + 6, 2, 2);

  // Legs (animated)
  ctx.fillStyle = "#1e3a5f";
  if (frame % 2 === 0) {
    ctx.fillRect(x + 6, y + 30, 4, 10);
    ctx.fillRect(x + 12, y + 30, 4, 8);
  } else {
    ctx.fillRect(x + 6, y + 30, 4, 8);
    ctx.fillRect(x + 12, y + 30, 4, 10);
  }

  // Sign (HOW DARE YOU)
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(x + 20, y + 4, 36, 14);
  ctx.strokeStyle = "#64748b";
  ctx.lineWidth = 1;
  ctx.strokeRect(x + 20, y + 4, 36, 14);
  ctx.fillStyle = "#dc2626";
  ctx.font = "bold 6px monospace";
  ctx.fillText("FACT", x + 23, y + 12);
  ctx.fillText("CHECK!", x + 23, y + 17);

  // Stick for sign
  ctx.fillStyle = "#92400e";
  ctx.fillRect(x + 19, y + 14, 2, 18);

  ctx.restore();
}

// Obstacles: CO2 clouds, factory smokestacks, oil barrels
function drawObstacle(ctx, type, x, y) {
  ctx.save();
  if (type === 0) {
    // Factory smokestack
    ctx.fillStyle = "#475569";
    ctx.fillRect(x, y, 16, 30);
    ctx.fillRect(x - 4, y + 22, 24, 8);
    // Smoke
    ctx.fillStyle = "#94a3b8";
    ctx.beginPath();
    ctx.arc(x + 8, y - 6, 6, 0, Math.PI * 2);
    ctx.arc(x + 14, y - 12, 5, 0, Math.PI * 2);
    ctx.fill();
  } else if (type === 1) {
    // Oil barrel
    ctx.fillStyle = "#1e293b";
    ctx.fillRect(x, y + 8, 18, 22);
    ctx.fillStyle = "#dc2626";
    ctx.fillRect(x + 2, y + 14, 14, 6);
    ctx.fillStyle = "#fbbf24";
    ctx.font = "bold 8px monospace";
    ctx.fillText("CO2", x + 2, y + 20);
  } else {
    // Fake news paper
    ctx.fillStyle = "#fef3c7";
    ctx.fillRect(x, y + 10, 22, 20);
    ctx.fillStyle = "#92400e";
    ctx.fillRect(x + 1, y + 11, 20, 4);
    ctx.fillStyle = "#dc2626";
    ctx.font = "bold 5px monospace";
    ctx.fillText("FAKE", x + 3, y + 14);
    ctx.fillText("NEWS", x + 3, y + 28);
  }
  ctx.restore();
}

export default function RunnerGame() {
  const canvasRef = useRef(null);
  const stateRef = useRef({
    gretaY: GROUND_Y - 40,
    velY: 0,
    jumping: false,
    obstacles: [{ x: CANVAS_W + 50, type: 0 }],
    score: 0,
    frame: 0,
    speed: GAME_SPEED_INIT,
    gameOver: false,
  });

  const [score, setScore] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    function jump() {
      const s = stateRef.current;
      if (!s.jumping && !s.gameOver) {
        s.velY = JUMP_FORCE;
        s.jumping = true;
      }
      if (s.gameOver) {
        // Reset
        s.gretaY = GROUND_Y - 40;
        s.velY = 0;
        s.jumping = false;
        s.obstacles = [{ x: CANVAS_W + 50, type: 0 }];
        s.score = 0;
        s.speed = GAME_SPEED_INIT;
        s.gameOver = false;
      }
    }

    function handleKey(e) {
      if (e.code === "Space" || e.code === "ArrowUp") {
        e.preventDefault();
        jump();
      }
    }

    function handleClick() {
      jump();
    }

    window.addEventListener("keydown", handleKey);
    canvas.addEventListener("click", handleClick);

    let animId;
    function loop() {
      const s = stateRef.current;
      s.frame++;

      // Clear
      ctx.fillStyle = "#f8fafc";
      ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

      // Ground
      ctx.strokeStyle = "#cbd5e1";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, GROUND_Y);
      ctx.lineTo(CANVAS_W, GROUND_Y);
      ctx.stroke();

      // Ground texture
      ctx.fillStyle = "#e2e8f0";
      for (let i = 0; i < CANVAS_W; i += 20) {
        const offset = (s.frame * s.speed) % 20;
        ctx.fillRect(i - offset, GROUND_Y + 3, 8, 2);
      }

      if (!s.gameOver) {
        // Physics
        s.velY += GRAVITY;
        s.gretaY += s.velY;
        if (s.gretaY >= GROUND_Y - 40) {
          s.gretaY = GROUND_Y - 40;
          s.velY = 0;
          s.jumping = false;
        }

        // Obstacles
        for (let obs of s.obstacles) {
          obs.x -= s.speed;
        }

        // Remove off-screen, spawn new
        s.obstacles = s.obstacles.filter((o) => o.x > -30);
        const last = s.obstacles[s.obstacles.length - 1];
        if (!last || last.x < CANVAS_W - 200 - Math.random() * 200) {
          s.obstacles.push({
            x: CANVAS_W + 20,
            type: Math.floor(Math.random() * 3),
          });
        }

        // Score
        s.score++;
        if (s.score % 100 === 0) {
          s.speed += 0.3;
        }
        setScore(Math.floor(s.score / 10));

        // Collision
        const gretaBox = { x: 50 + 4, y: s.gretaY + 2, w: 14, h: 38 };
        for (let obs of s.obstacles) {
          const obsBox = { x: obs.x, y: GROUND_Y - 30, w: 20, h: 30 };
          if (
            gretaBox.x < obsBox.x + obsBox.w &&
            gretaBox.x + gretaBox.w > obsBox.x &&
            gretaBox.y + gretaBox.h > obsBox.y
          ) {
            s.gameOver = true;
          }
        }
      }

      // Draw Greta
      const walkFrame = Math.floor(s.frame / 8);
      drawGreta(ctx, 50, s.gretaY, walkFrame);

      // Draw obstacles
      for (let obs of s.obstacles) {
        drawObstacle(ctx, obs.type, obs.x, GROUND_Y - 30);
      }

      // Score
      ctx.fillStyle = "#64748b";
      ctx.font = "bold 14px monospace";
      ctx.fillText(`Score: ${Math.floor(s.score / 10)}`, CANVAS_W - 120, 20);

      // Game over
      if (s.gameOver) {
        ctx.fillStyle = "rgba(248, 250, 252, 0.8)";
        ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
        ctx.fillStyle = "#0f172a";
        ctx.font = "bold 20px 'DM Sans', sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Misinformation got you!", CANVAS_W / 2, 70);
        ctx.font = "14px 'DM Sans', sans-serif";
        ctx.fillStyle = "#64748b";
        ctx.fillText("Click or press Space to try again", CANVAS_W / 2, 100);
        ctx.textAlign = "left";
      }

      animId = requestAnimationFrame(loop);
    }

    animId = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("keydown", handleKey);
      canvas.removeEventListener("click", handleClick);
    };
  }, []);

  return (
    <div className="runner-game">
      <p className="runner-hint">Jump over misinformation while we analyze! (Space / Click)</p>
      <canvas
        ref={canvasRef}
        width={CANVAS_W}
        height={CANVAS_H}
        className="runner-canvas"
      />
    </div>
  );
}
