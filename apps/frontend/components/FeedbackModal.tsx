'use client';

import { useState } from 'react';
import { submitFeedback } from '../lib/api';

export default function FeedbackModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [type, setType] = useState('bug');
  const [message, setMessage] = useState('');
  const [rating, setRating] = useState(5);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await submitFeedback(type, message, rating);
      setSubmitted(true);
      setTimeout(() => {
        setIsOpen(false);
        setSubmitted(false);
        setMessage('');
      }, 2000);
    } catch (error) {
      console.error(error);
    }
  };

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 bg-gray-800 text-gray-400 p-2 rounded-full shadow-lg hover:bg-gray-700 hover:text-white transition-colors"
        title="Send Feedback"
      >
        💬
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 bg-gray-800 border border-gray-700 p-6 rounded-lg shadow-2xl w-80 z-50">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-white">Feedback</h3>
        <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-white">✕</button>
      </div>

      {submitted ? (
        <div className="text-green-400 text-center py-4">Thank you for your feedback!</div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Type</label>
            <select 
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full bg-gray-700 border-gray-600 text-white rounded p-2"
            >
              <option value="bug">Report Bug</option>
              <option value="feature">Request Feature</option>
              <option value="rating">Rate Us</option>
            </select>
          </div>

          {type === 'rating' && (
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Rating</label>
              <div className="flex space-x-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRating(star)}
                    className={`text-xl ${rating >= star ? 'text-yellow-400' : 'text-gray-600'}`}
                  >
                    ★
                  </button>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Message</label>
            <textarea 
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="w-full bg-gray-700 border-gray-600 text-white rounded p-2 h-24"
              placeholder="Tell us what you think..."
              required
            />
          </div>

          <button 
            type="submit"
            className="w-full bg-purple-600 hover:bg-purple-700 text-white py-2 rounded font-medium"
          >
            Submit
          </button>
        </form>
      )}
    </div>
  );
}
