import { test, expect } from '@playwright/test';

test.describe('Chat UI with MCP browser-use integration', () => {
  test('navigates to test page and returns title', async ({ page }) => {
    test.skip(!process.env.OPENAI_API_KEY, 'No LLM key configured');

    // Open UI
    await page.goto('/');

    // Find chat input
    const input = page.getByPlaceholder('Type your message...');
    await expect(input).toBeVisible();

    // Compose deterministic instruction to use browser tools
    const msg = `Use browser tools:
1) go_to_url to 'http://server:8001/api/testpage'
2) extract_structured_data with query 'the exact page title text'
3) done when finished`;

    await input.fill(msg);
    await input.press('Enter');

    // Wait for response to include expected title
    await expect(page.getByText('MCP Browser Test Page')).toBeVisible({ timeout: 180_000 });
  });
});
