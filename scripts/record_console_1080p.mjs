import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

async function main() {
  const videoDir = path.resolve('docs/demo/raw_video');
  if (fs.existsSync(videoDir)) {
    fs.rmSync(videoDir, { recursive: true, force: true });
  }
  fs.mkdirSync(videoDir, { recursive: true });

  console.log('Launching browser at 1920x1080...');
  const browser = await chromium.launch({
    headless: true
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: {
      dir: videoDir,
      size: { width: 1920, height: 1080 }
    }
  });

  const page = await context.newPage();
  console.log('Navigating to http://127.0.0.1:8630...');
  await page.goto('http://127.0.0.1:8630/', { waitUntil: 'networkidle' });

  // Wait for connection indicator
  await page.waitForSelector('#conn[data-state="up"]', { timeout: 15000 });
  console.log('Connected! Holding initial screen for 2s...');
  await page.waitForTimeout(2000);

  // Question 1: Click chip
  console.log('Clicking Question 1: Sneha Iyer orders...');
  await page.click('button[data-q="What did Sneha Iyer order, exactly?"]');
  await page.waitForSelector('#send:not([disabled])', { timeout: 40000 });
  console.log('Q1 answered! Holding for 2.5s...');
  await page.waitForTimeout(2500);

  // Question 2: Type naturally
  console.log('Typing Question 2: Draft orders...');
  await page.type('#input', 'Which orders are still in draft status?', { delay: 40 });
  await page.waitForTimeout(500);
  await page.click('#send');
  await page.waitForSelector('#send:not([disabled])', { timeout: 40000 });
  console.log('Q2 answered! Holding for 2.5s...');
  await page.waitForTimeout(2500);

  // Question 3: Type naturally
  console.log('Typing Question 3: Jaipur bedsheets in stock...');
  await page.type('#input', 'Do we stock Jaipur bedsheets, and at what price?', { delay: 40 });
  await page.waitForTimeout(500);
  await page.click('#send');
  await page.waitForSelector('#send:not([disabled])', { timeout: 40000 });
  console.log('Q3 answered! Holding final state for 7s...');
  await page.waitForTimeout(7000);

  await page.close();
  await context.close();
  await browser.close();

  const files = fs.readdirSync(videoDir).filter(f => f.endsWith('.webm'));
  console.log('Finished recording! Files:', files);
}

main().catch(err => {
  console.error('Recording error:', err);
  process.exit(1);
});
