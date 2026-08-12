import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import Dashboard from './pages/Dashboard';
import Papers from './pages/Papers';
import PaperDetail from './pages/PaperDetail';
import Agent from './pages/Agent';
import Graph from './pages/Graph';

export default function App() {
  return (
    <BrowserRouter>
      <Header />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/papers" element={<Papers />} />
        <Route path="/papers/:paperId" element={<PaperDetail />} />
        <Route path="/agent" element={<Agent />} />
        <Route path="/graph" element={<Graph />} />
      </Routes>
      <Footer />
    </BrowserRouter>
  );
}
