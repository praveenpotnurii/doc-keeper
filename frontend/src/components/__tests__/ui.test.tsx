// Import tests for UI components that don't depend on axios
describe('UI Component Imports', () => {
  test('can import Button component', async () => {
    const { Button } = await import('../ui/button');
    expect(Button).toBeDefined();
    // Button is a React component (object), not a plain function
    expect(typeof Button).toBe('object');
  });

  test('can import Card components', async () => {
    const { Card, CardContent, CardDescription, CardHeader, CardTitle } = await import('../ui/card');
    expect(Card).toBeDefined();
    expect(CardContent).toBeDefined();
    expect(CardDescription).toBeDefined();
    expect(CardHeader).toBeDefined();
    expect(CardTitle).toBeDefined();
  });

  test('can import Input component', async () => {
    const { Input } = await import('../ui/input');
    expect(Input).toBeDefined();
    // Input is a React component (object), not a plain function
    expect(typeof Input).toBe('object');
  });

  test('can import Dialog components', async () => {
    const { Dialog, DialogContent, DialogHeader, DialogTitle } = await import('../ui/dialog');
    expect(Dialog).toBeDefined();
    expect(DialogContent).toBeDefined();
    expect(DialogHeader).toBeDefined();
    expect(DialogTitle).toBeDefined();
  });

  test('can import ThemeToggle component', async () => {
    const { ThemeToggle } = await import('../ui/theme-toggle');
    expect(ThemeToggle).toBeDefined();
    expect(typeof ThemeToggle).toBe('function');
  });
});