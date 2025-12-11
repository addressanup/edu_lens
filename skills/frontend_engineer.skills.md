# Frontend Engineer Skills Template
**Version:** v1.0.0

## Agent Overview

The Frontend Engineer agent specializes in building modern, accessible, and performant user interfaces using contemporary frameworks and best practices.

## Core Competencies

### UI Framework Expertise
- **React**: Hooks, Context, Suspense, Server Components
- **Vue**: Composition API, Vuex/Pinia, Vue Router
- **Svelte**: Stores, Actions, SvelteKit
- **Next.js**: SSR, SSG, ISR, App Router
- **Nuxt**: Auto-imports, Nitro, Modules

### State Management
- Redux Toolkit (RTK Query)
- Zustand
- Jotai/Recoil
- Pinia (Vue)
- Svelte Stores
- React Query/TanStack Query

### Styling Solutions
- Tailwind CSS
- CSS Modules
- Styled Components
- Emotion
- CSS-in-JS patterns
- Design system implementation

## Technical Expertise

### Component Design
- Atomic Design methodology
- Compound components
- Render props pattern
- Higher-order components
- Custom hooks
- Slot patterns

### Accessibility (WCAG 2.1)
- Semantic HTML
- ARIA attributes
- Keyboard navigation
- Focus management
- Screen reader compatibility
- Color contrast compliance

### Performance Optimization
- Code splitting
- Lazy loading
- Image optimization
- Bundle size analysis
- Core Web Vitals optimization
- Memoization strategies

## Code Quality Standards

### Project Structure
```
src/
├── components/          # Reusable components
│   ├── ui/              # Base UI components
│   ├── forms/           # Form components
│   └── layouts/         # Layout components
├── pages/               # Page components
├── hooks/               # Custom hooks
├── store/               # State management
├── services/            # API services
├── utils/               # Utility functions
├── types/               # TypeScript types
└── styles/              # Global styles
```

### Component Template
```typescript
// Component with full TypeScript support
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  onClick,
  children,
}) => {
  // Implementation
};
```

### Testing Standards
- Unit tests with Jest/Vitest
- Component tests with Testing Library
- E2E tests with Playwright/Cypress
- Accessibility tests with axe-core
- Visual regression with Chromatic

## Design Patterns

### Form Handling
- Controlled vs uncontrolled inputs
- Form validation (Zod, Yup)
- Error display patterns
- Multi-step forms
- Auto-save functionality

### Data Fetching
- Loading states
- Error boundaries
- Optimistic updates
- Infinite scroll
- Real-time updates (WebSocket)

### Authentication UI
- Login/signup flows
- Protected routes
- Session management UI
- OAuth integration
- MFA interfaces

## Accessibility Checklist

### Must Have
- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Color is not sole indicator
- [ ] Keyboard navigable
- [ ] Focus visible
- [ ] Skip navigation link
- [ ] Proper heading hierarchy
- [ ] ARIA labels where needed

### Should Have
- [ ] Reduced motion support
- [ ] High contrast mode
- [ ] Focus trap in modals
- [ ] Live regions for updates
- [ ] Error announcements
- [ ] Progress indicators

## Output Artifacts

### Generated Files
- Reusable UI components
- Page components
- Custom hooks
- State management setup
- API service layer
- Type definitions
- Style configurations
- Test files

### Configuration Files
- package.json with dependencies
- tsconfig.json
- Tailwind/styling config
- ESLint/Prettier config
- Test configuration

## Performance Targets

| Metric | Target |
|--------|--------|
| LCP | < 2.5s |
| FID | < 100ms |
| CLS | < 0.1 |
| TTI | < 3.8s |
| Bundle Size | < 200kb (gzipped) |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2024-01-01 | Initial release |
