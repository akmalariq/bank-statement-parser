# 🚀 Deployment Guide (GitHub Pages)

I have organized your project so you can deploy it in **3 clicks**.

Your "Browser-Only" app is located in the `docs/` folder. GitHub Pages loves this folder.

## Step 1: Push to GitHub
Open your terminal in VS Code (or your git tool) and run:
```bash
git add .
git commit -m "Prepare for deployment"
git push
```

## Step 2: Turn on GitHub Pages
1. Go to your **GitHub Repository** in your browser.
2. Click **Settings** (top right tab).
3. On the left sidebar, click **Pages**.
4. Under "Build and deployment" > "Branch":
   - Select **main**
   - Select folder **`/docs`** (IMPORTANT: Do not select `/root`)
5. Click **Save**.

## Step 3: Done!
Wait about 60 seconds. Refresh the Pages settings page.
You will see a link like:
`https://your-username.github.io/bank-statement-parser/`

## Try it
Open that link on your phone, your friend's laptop, anywhere.
- It loads instantly.
- Upload a file.
- Watch it parse **in the browser** (no backend server!).
