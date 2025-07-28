# Deployment Guide for FinVault

## Render Deployment Instructions

### **Default Behavior**
Render automatically runs the following commands for Node.js/React projects:

```
npm install
npm run build
```

**You do NOT need to specify a custom build command unless you have a special requirement.**

---

### **Correct Setup**
- **Build Command:** (leave blank, or use the default)
- **Publish Directory:** `frontend/dist`

---

### **Common Mistake: Double Build**
**Do NOT set the build command to `npm install && npm run build` or run `npm run build` manually in your custom build command.**

- This causes the build to run twice, which can lead to:
  - Broken or unstyled CSS
  - Incomplete or corrupted build output
  - Hard-to-debug deployment issues

---

### **Troubleshooting**
- If your site is unstyled or the build output is incorrect:
  1. **Check your build command:** Make sure you are not running `npm run build` twice.
  2. **Let Render handle the build:** Only use a custom build command if you need something different from the default.
  3. **Verify your `dist/` output:** The CSS should be processed and not contain any `@tailwind` directives.

---

### **Removing Dev-Only Scripts**
If you see a Replit banner or other dev-only scripts in production, remove the corresponding `<script>` tag from `frontend/client/index.html`.

---

### **Summary Table**
| Step                | What to Do                                      |
|---------------------|-------------------------------------------------|
| Build Command       | Leave blank (default: npm install & npm run build) |
| Publish Directory   | `frontend/dist`                                 |
| Dev-only Scripts    | Remove from `index.html` for production         |

---

**Following these steps will ensure a smooth, styled, and reliable deployment on Render.** 