# Canada.ca Typography Compliance Implementation Plan

## Overview

Transform Nachet frontend from current Arial/vh-based typography to Canada.ca mandatory standards (Lato/Noto Sans with specific px sizes).

---

## Phase 1: Foundation - Font Imports & Theme Setup (2-3 hours)

### 1.1 Import Required Fonts

**File:** `frontend/index.html`

Add Google Fonts links in `<head>`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700&family=Noto+Sans:wght@400&display=swap" rel="stylesheet">
```

**File:** `frontend/src/index.css` (lines 2, 22, 28)

Replace Arial with Noto Sans:

```css
html {
  font-family: 'Noto Sans', sans-serif;
}

body {
  font-family: 'Noto Sans', sans-serif;
}
```

### 1.2 Create MUI Theme Configuration

**File:** `frontend/src/theme/canadaTheme.ts` (NEW)

```typescript
import { createTheme } from '@mui/material/styles';

export const canadaTheme = createTheme({
  typography: {
    fontFamily: "'Noto Sans', sans-serif",

    // Headings use Lato
    h1: {
      fontFamily: "'Lato', sans-serif",
      fontWeight: 700,
      fontSize: '41px',
      '@media (max-width:600px)': {
        fontSize: '37px',
      },
    },
    h2: {
      fontFamily: "'Lato', sans-serif",
      fontWeight: 700,
      fontSize: '39px',
      '@media (max-width:600px)': {
        fontSize: '35px',
      },
    },
    h3: {
      fontFamily: "'Lato', sans-serif",
      fontWeight: 700,
      fontSize: '29px',
      '@media (max-width:600px)': {
        fontSize: '26px',
      },
    },
    h4: {
      fontFamily: "'Lato', sans-serif",
      fontWeight: 700,
      fontSize: '27px',
      '@media (max-width:600px)': {
        fontSize: '22px',
      },
    },
    h5: {
      fontFamily: "'Lato', sans-serif",
      fontWeight: 700,
      fontSize: '24px',
      '@media (max-width:600px)': {
        fontSize: '20px',
      },
    },
    h6: {
      fontFamily: "'Lato', sans-serif",
      fontWeight: 700,
      fontSize: '22px',
      '@media (max-width:600px)': {
        fontSize: '18px',
      },
    },

    // Body text uses Noto Sans
    body1: {
      fontSize: '20px',
      '@media (max-width:600px)': {
        fontSize: '18px',
      },
    },
    body2: {
      fontSize: '18px',
      '@media (max-width:600px)': {
        fontSize: '16px',
      },
    },
  },

  palette: {
    primary: {
      main: '#26374A', // Canada.ca main accent
    },
    error: {
      main: '#d3080c', // Canada.ca error color
    },
    text: {
      primary: '#333', // Canada.ca text color
    },
  },

  components: {
    MuiLink: {
      styleOverrides: {
        root: {
          color: '#284162', // Canada.ca default link
          textDecoration: 'underline',
          textDecorationSkipInk: 'auto',
          '&:hover, &:focus': {
            color: '#0535d2', // Canada.ca selected link
          },
          '&:visited': {
            color: '#7834bc', // Canada.ca visited link
          },
        },
      },
    },
  },
});
```

### 1.3 Wrap App with ThemeProvider

**File:** `frontend/src/main.tsx`

Add import:

```typescript
import { ThemeProvider } from '@mui/material/styles';
import { canadaTheme } from './theme/canadaTheme';
```

Wrap the app (around line 140-148):

```typescript
<ThemeProvider theme={canadaTheme}>
  <CacheProvider value={emotionCache}>
    <I18nextProvider i18n={i18n}>
      <App />
    </I18nextProvider>
  </CacheProvider>
</ThemeProvider>
```

---

## Phase 2: Update Color Palette (1-2 hours)

### 2.1 Extend colours.tsx

**File:** `frontend/src/styles/colours.tsx`

Add Canada.ca required colors:

```typescript
export const colours = {
  // Existing CFIA colors
  CFIA_Background_Blue: "#05486C",
  CFIA_Background_White: "#FFF",
  CFIA_Font_White: "#FFF",
  CFIA_Font_Black: "#333",
  CFIA_Font_Gray: "#999",

  // Canada.ca mandatory colors
  Canada_Red: "#A62A1E",           // H1 red bar
  Canada_Text: "#333",              // Body text (same as CFIA_Font_Black)
  Canada_Link_Default: "#284162",   // Default link
  Canada_Link_Selected: "#0535d2",  // Hover/focus link
  Canada_Link_Visited: "#7834bc",   // Visited link
  Canada_Accent: "#26374A",         // Main accent
  Canada_Error: "#d3080c",          // Error indicator
  Canada_Background_White: "#FFF",  // Default background
};
```

---

## Phase 3: Component Migration - Typography (8-12 hours)

### 3.1 Convert vh-based sizes to theme values

**Priority Component Updates:**

#### A. AppBar.tsx (line 51)

**Current:**

```tsx
<Typography variant="h2" sx={{ fontSize: "1.4vh" }}>
```

**Update to:**

```tsx
<Typography variant="h2">
  {/* Remove fontSize override - use theme */}
```

#### B. ModelPopup.tsx (lines 81, 146)

**Current:**

```tsx
<Typography variant="h6" sx={{ fontSize: "1.8vh" }}>
<Typography fontSize={20} variant="h6">
```

**Update to:**

```tsx
<Typography variant="h6">
  {/* Remove fontSize override */}
```

#### C. ErrorBoundary.tsx (line 76)

**Current:**

```tsx
<Typography variant="h4" color="error" gutterBottom>
```

**Keep as-is** (already using theme variant correctly)

### 3.2 Add Missing H1 Elements

Identify main pages and add H1 titles:

**Example for main page:**

```tsx
import { PageTitle } from '@components/common/PageTitle';

function MainPage() {
  return (
    <>
      <PageTitle>Nachet Seed Identification</PageTitle>
      {/* Rest of page content */}
    </>
  );
}
```

**Pages needing H1:**

- Main dashboard/home page
- Upload page
- Results page
- Settings/configuration pages

### 3.3 Create H1 Red Bar Component

**File:** `frontend/src/components/common/PageTitle.tsx` (NEW)

```tsx
import { Typography, Box } from '@mui/material';
import { colours } from '@styles/colours';

interface PageTitleProps {
  children: React.ReactNode;
}

export const PageTitle: React.FC<PageTitleProps> = ({ children }) => {
  return (
    <Box sx={{ mb: 4 }}>
      <Typography
        variant="h1"
        component="h1"
        sx={{ mb: '0.2em' }}
      >
        {children}
      </Typography>
      <Box
        sx={{
          width: '72px',
          height: '6px',
          backgroundColor: colours.Canada_Red,
        }}
      />
    </Box>
  );
};
```

**Export from index:**
**File:** `frontend/src/components/common/index.ts`

Add:

```typescript
export { PageTitle } from './PageTitle';
```

---

## Phase 4: Link Styling & Accessibility (3-4 hours)

### 4.1 Remove textDecoration: "none"

#### A. Footer.tsx (lines 79-84)

**Current:**

```tsx
<Link href="https://github.com/ai-cfia"
  sx={{
    color: colours.CFIA_Font_Black,
    fontSize: "1rem",
    textDecoration: "none",  // ❌ Remove this
    cursor: "pointer",
  }}
>
```

**Update to:**

```tsx
<Link href="https://github.com/ai-cfia"
  sx={{
    color: colours.Canada_Link_Default,  // Use Canada.ca color
    fontSize: "1rem",
    // textDecoration handled by theme
    cursor: "pointer",
  }}
>
```

#### B. AppBar.tsx (line 56)

**Current:**

```tsx
textDecoration: "none"  // ❌ Remove this
```

**Update to:**

```tsx
// Remove textDecoration property entirely
// Let theme handle link styling
```

### 4.2 Search for All Instances

Use Grep to find all `textDecoration: "none"` and update each occurrence.

### 4.3 Global Link Styles (if needed)

**File:** `frontend/src/index.css`

Add:

```css
a {
  text-decoration: underline;
  text-decoration-skip-ink: auto;
}
```

---

## Phase 5: Line Length Constraints (2-3 hours)

### 5.1 Add max-width to Content Containers

**File:** `frontend/src/root/body/body.tsx`

Wrap text content in constrained container:

```tsx
<Box sx={{ maxWidth: '65ch', mx: 'auto', px: 2 }}>
  {/* Text content here */}
</Box>
```

### 5.2 Apply to Text-Heavy Components

- Error messages
- Description text
- Form help text
- Information panels

**Example pattern:**

```tsx
<Typography variant="body1" sx={{ maxWidth: '65ch' }}>
  Long descriptive text that should be constrained...
</Typography>
```

### 5.3 Important Note

Page layouts can be wider than 65ch - only **lines of text** should be constrained for readability.

---

## Phase 6: Responsive Typography (3-4 hours)

### 6.1 Verify Breakpoint Logic in Theme

The theme created in Phase 1.2 already includes responsive breakpoints. Verify it works correctly.

### 6.2 Test Across Devices

**Desktop sizes to test:**

- 1920px (Full HD)
- 1440px (Laptop)
- 1024px (Tablet landscape)

**Mobile sizes to test:**

- 768px (Tablet portrait)
- 414px (iPhone Plus)
- 375px (iPhone)

### 6.3 Use Browser DevTools

1. Open DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Test each breakpoint
4. Verify font sizes match specifications

---

## Phase 7: Testing & Validation (4-6 hours)

### 7.1 Visual Regression Testing

- Take screenshots of all major pages before changes
- Take screenshots after each phase
- Compare for layout breakage
- Document any intentional visual changes

### 7.2 Accessibility Testing

**Tools:**

- Chrome Lighthouse (Accessibility score)
- axe DevTools browser extension
- WAVE browser extension

**Checklist:**

- [ ] WCAG AAA contrast ratios (4.5:1 minimum)
- [ ] Links visually distinguishable from text
- [ ] Focus indicators visible on all interactive elements
- [ ] Keyboard navigation works correctly
- [ ] Screen reader announces headings properly

### 7.3 Cross-Browser Testing

**Required browsers:**

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

**Check:**

- Font rendering consistency
- Link underlines display correctly
- Responsive breakpoints work
- No layout shifts

### 7.4 Manual Compliance Checklist

**Typography:**

- [ ] Lato loads for all headings (h1-h6)
- [ ] Lato uses bold weight (700) for headings
- [ ] Noto Sans loads for all body text
- [ ] Desktop font sizes: H1=41px, H2=39px, H3=29px, H4=27px, H5=24px, H6=22px, Body=20px
- [ ] Mobile font sizes: H1=37px, H2=35px, H3=26px, H4=22px, H5=20px, H6=18px, Body=18px

**Colors:**

- [ ] Text color is #333
- [ ] Default link color is #284162
- [ ] Hover/focus link color is #0535d2
- [ ] Visited link color is #7834bc
- [ ] Main accent color is #26374A
- [ ] Error color is #d3080c

**Elements:**

- [ ] H1 red bars present on main pages
- [ ] Red bar is #A62A1E, 72px wide, 6px thick
- [ ] Red bar positioned 0.2em below H1
- [ ] All links underlined
- [ ] Link underlines skip descenders (text-decoration-skip-ink: auto)

**Layout:**

- [ ] Text line length ≤ 65 characters
- [ ] Page layouts can be wider than 65ch
- [ ] Majority of page has white background

---

## Phase 8: Documentation (1-2 hours)

### 8.1 Update CLAUDE.md

Add section:

```markdown
## Canada.ca Design System Compliance

Nachet follows the mandatory requirements of the Canada.ca Web Design System:

### Typography
- **Fonts**: Lato (headings), Noto Sans (body text)
- **Sizes**: Desktop (H1: 41px, Body: 20px), Mobile (H1: 37px, Body: 18px)
- **Line length**: Maximum 65 characters for text content
- **H1 styling**: Red bar (#A62A1E, 72px × 6px) 0.2em below main page titles

### Colors
- **Text**: #333
- **Links**: #284162 (default), #0535d2 (hover), #7834bc (visited)
- **Accent**: #26374A
- **Error**: #d3080c
- **Background**: White (#FFF) for majority of page

### Links
- All links must be underlined with descender-skipping (text-decoration-skip-ink: auto)

**Reference**: https://design.canada.ca/
```

### 8.2 Create Component Usage Guide

**File:** `frontend/docs/CANADA_CA_COMPONENT_GUIDE.md` (NEW)

```markdown
# Canada.ca Component Usage Guide

## Typography Components

### Page Titles (H1)
Always use the `PageTitle` component for main page headings:

```tsx
import { PageTitle } from '@components/common/PageTitle';

<PageTitle>Page Title Here</PageTitle>
```

This automatically includes the Canada.ca mandatory red bar.

### Section Headings

Use MUI Typography with appropriate variant:

```tsx
<Typography variant="h2">Section Heading</Typography>
<Typography variant="h3">Subsection</Typography>
```

**DO NOT** override fontSize with sx prop - let theme handle sizing.

### Body Text

```tsx
<Typography variant="body1">Regular paragraph text</Typography>
<Typography variant="body2">Smaller text (captions, etc.)</Typography>
```

### Links

Use MUI Link component - theme handles Canada.ca styling:

```tsx
import { Link } from '@mui/material';

<Link href="/path">Link text</Link>
```

**DO NOT** add `textDecoration: "none"` - links must be underlined per Canada.ca.

## Common Mistakes to Avoid

❌ **Don't** use inline fontSize overrides:

```tsx
<Typography variant="h2" sx={{ fontSize: "1.4vh" }}>  // Bad
```

✅ **Do** use theme variants:

```tsx
<Typography variant="h2">  // Good
```

❌ **Don't** remove link underlines:

```tsx
<Link sx={{ textDecoration: "none" }}>  // Bad
```

✅ **Do** let theme handle styling:

```tsx
<Link href="/path">  // Good
```

❌ **Don't** use arbitrary colors:

```tsx
<Typography sx={{ color: "#666" }}>  // Bad
```

✅ **Do** use theme or Canada.ca colors:

```tsx
<Typography color="text.primary">  // Good
import { colours } from '@styles/colours';
<Typography sx={{ color: colours.Canada_Text }}>  // Also good
```

## Line Length for Readability

Wrap text content in max-width containers:

```tsx
<Box sx={{ maxWidth: '65ch' }}>
  <Typography variant="body1">
    Long paragraph text that should be constrained...
  </Typography>
</Box>
```

Note: Page layouts can be wider - only text content should be constrained.

```text

---

## Summary

### Estimated Total Effort: 24-36 hours

**Breakdown:**
- Phase 1 (Foundation): 2-3 hours
- Phase 2 (Colors): 1-2 hours
- Phase 3 (Components): 8-12 hours
- Phase 4 (Links): 3-4 hours
- Phase 5 (Line Length): 2-3 hours
- Phase 6 (Responsive): 3-4 hours
- Phase 7 (Testing): 4-6 hours
- Phase 8 (Documentation): 1-2 hours

### Priority Levels

**🚨 Critical (Must Have):**
- Phases 1-4 → 14-21 hours
- Font imports, theme setup, component updates, link styling

**⚠️ High (Should Have):**
- Phases 5-6 → 5-7 hours
- Line length, responsive typography

**✅ Important (Nice to Have):**
- Phases 7-8 → 5-8 hours
- Comprehensive testing, documentation

### Key Files to Create
1. `frontend/src/theme/canadaTheme.ts`
2. `frontend/src/components/common/PageTitle.tsx`
3. `frontend/docs/CANADA_CA_COMPONENT_GUIDE.md`

### Key Files to Modify
1. `frontend/index.html` (add font imports)
2. `frontend/src/index.css` (remove Arial, add Noto Sans)
3. `frontend/src/main.tsx` (wrap with ThemeProvider)
4. `frontend/src/styles/colours.tsx` (add Canada.ca colors)
5. `frontend/src/components/common/index.ts` (export PageTitle)
6. 30+ component files (remove fontSize overrides, restore link underlines)

### Risk Mitigation Strategies

1. **Version Control**
   - Create feature branch: `feature/canada-ca-typography-compliance`
   - Commit after each phase
   - Keep original branch as fallback

2. **Incremental Testing**
   - Test after each phase
   - Don't proceed if critical issues found
   - Document any breaking changes

3. **Stakeholder Communication**
   - Visual changes are significant
   - Share before/after screenshots with CFIA team
   - Get approval on font sizes (users may find 20px body text large)

4. **Rollback Plan**
   - Keep screenshots of original design
   - Document all color/size changes
   - Ability to revert to pre-compliance state if needed

5. **Performance**
   - Monitor Google Fonts loading time
   - Consider self-hosting fonts if performance issues
   - Use font-display: swap for better perceived performance

### Success Criteria

**Technical:**
- All 6 mandatory requirements met (fonts, sizes, H1 bars, line length, links, responsive)
- Zero accessibility violations in axe/WAVE
- WCAG AAA compliance achieved

**User Experience:**
- No broken layouts
- All text readable and properly sized
- Links clearly distinguishable
- Consistent experience across devices

**Compliance:**
- Passes Canada.ca design system validation
- CFIA stakeholder approval obtained
- Documentation complete for future developers

---

**Next Steps:** Create feature branch and begin Phase 1 when ready to proceed.
