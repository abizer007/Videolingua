# VidioLingua Frontend

A modern React frontend for the VidioLingua video translation platform, built for Techgium Proof of Concept.

## Features

- **Landing Page**: Professional introduction with problem statement, solution, and how it works
- **Demo Page**: Interactive video upload and processing interface
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Clean UI**: Modern, professional design with smooth animations
- **Backend Integration**: Ready to connect with VidioLingua backend API

## Tech Stack

- React 18
- Vite
- React Router
- Plain CSS (no frameworks)
- Fetch API

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The application will open at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

The production build will be in the `dist` folder.

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable components
│   │   ├── Header.jsx
│   │   ├── Footer.jsx
│   │   ├── Button.jsx
│   │   └── ResultCard.jsx
│   ├── pages/           # Page components
│   │   ├── Landing.jsx
│   │   └── Demo.jsx
│   ├── services/        # API services
│   │   └── api.js
│   ├── styles/          # CSS files
│   │   ├── index.css
│   │   ├── App.css
│   │   ├── Header.css
│   │   ├── Footer.css
│   │   ├── Button.css
│   │   ├── ResultCard.css
│   │   ├── Landing.css
│   │   └── Demo.css
│   ├── App.jsx          # Main app component
│   └── main.jsx         # Entry point
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

## Backend Integration

The frontend is configured to connect to a backend API. By default, it expects the API at `http://localhost:8000`.

### Environment Variables

Create a `.env` file in the frontend directory to customize the API URL:

```
VITE_API_URL=http://localhost:8000
```

### API Endpoints

The frontend expects the following endpoint:

- `POST /api/process` - Process a video file
  - Body: FormData with `video` (file) and `target_language` (string)
  - Response: `{ status: "success", result: "...", confidence: 0.85 }`

### Mock Mode

If the backend is not available, the frontend will automatically use mock responses for demonstration purposes.

## Features for Judges

- **Clear Instructions**: Demo page includes step-by-step instructions
- **Visual Feedback**: Loading states and result cards provide clear feedback
- **Error Handling**: User-friendly error messages
- **Responsive Design**: Works on all device sizes

## Development

### Code Quality

- Functional components with React Hooks
- Reusable components
- Meaningful variable names
- Comments explaining logic
- Clean CSS with CSS variables for theming

### Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

Part of the VidioLingua Techgium PoC project.

