import Navbar from './components/Navbar'
import Hero from './components/Hero'
import TransformationAnimation from './components/TransformationAnimation'
import Features from './components/Features'
import CRMPreview from './components/CRMPreview'
import Stats from './components/Stats'
import CTA from './components/CTA'

export default function App() {
  return (
    <div className="bg-white min-h-screen overflow-x-hidden">
      <Navbar />
      <Hero />
      <TransformationAnimation />
      <Features />
      <CRMPreview />
      <Stats />
      <CTA />
    </div>
  )
}
