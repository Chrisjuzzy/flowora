import React, { useState, useEffect } from 'react';

const TUTORIAL_STEPS = [
  {
    title: "Welcome to Flowora",
    content: "Flowora lets you create, manage, and monetize autonomous AI agents.",
    target: "body" 
  },
  {
    title: "Create Your First Agent",
    content: "Click the 'Create Agent' button to start building. You can use templates or start from scratch.",
    target: "#create-agent-btn" 
  },
  {
    title: "Marketplace",
    content: "Discover agents built by others or publish your own to earn revenue.",
    target: "a[href='/marketplace']"
  },
  {
    title: "Innovation Layer",
    content: "Use advanced features like Autonomous Goals and Simulations to test your agents.",
    target: "a[href='/innovation']"
  }
];

export default function OnboardingTutorial() {
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Check if tutorial has been seen
    const seen = localStorage.getItem('tutorial_seen');
    if (!seen) {
      setIsVisible(true);
    }
  }, []);

  const handleNext = () => {
    if (currentStep < TUTORIAL_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleClose();
    }
  };

  const handleClose = () => {
    setIsVisible(false);
    localStorage.setItem('tutorial_seen', 'true');
  };

  if (!isVisible) return null;

  const step = TUTORIAL_STEPS[currentStep];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-gray-800 border border-gray-700 p-6 rounded-lg max-w-md shadow-2xl relative">
        <button 
          onClick={handleClose}
          className="absolute top-2 right-2 text-gray-400 hover:text-white"
        >
          ✕
        </button>
        
        <div className="mb-4">
          <span className="text-xs font-bold text-purple-400 uppercase tracking-wider">
            Step {currentStep + 1} of {TUTORIAL_STEPS.length}
          </span>
          <h3 className="text-xl font-bold text-white mt-1">{step.title}</h3>
        </div>
        
        <p className="text-gray-300 mb-6">{step.content}</p>
        
        <div className="flex justify-between items-center">
          <button 
            onClick={handleClose}
            className="text-gray-400 hover:text-white text-sm"
          >
            Skip Tutorial
          </button>
          <button 
            onClick={handleNext}
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded font-medium"
          >
            {currentStep === TUTORIAL_STEPS.length - 1 ? "Get Started" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
