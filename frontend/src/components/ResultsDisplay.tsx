import React, { useState } from 'react';
import { AnalysisResult, AIInsight } from '../App';

interface ResultsDisplayProps {
  results: AnalysisResult;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ results }) => {
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set());
  const [filterSeverity, setFilterSeverity] = useState<'all' | 'high' | 'critical'>('all');

  const toggleCard = (index: number) => {
    const newExpanded = new Set(expandedCards);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedCards(newExpanded);
  };

  const expandAll = () => {
    setExpandedCards(new Set(Array.from({ length: filteredInsights.length }, (_, i) => i)));
  };

  const collapseAll = () => {
    setExpandedCards(new Set());
  };

  const filteredInsights = results.insights.filter(insight => {
    switch (filterSeverity) {
      case 'critical':
        return insight.severity === 'critical';
      case 'high':
        return insight.severity === 'high' || insight.severity === 'critical';
      default:
        return true;
    }
  });

  const getFilterButtonClass = (level: string) => {
    const baseClass = "px-3 py-1 text-sm font-medium rounded-md transition-colors";
    if (filterSeverity === level) {
      return `${baseClass} bg-primary-100 dark:bg-primary-900/30 text-primary-800 dark:text-primary-200 border border-primary-200 dark:border-primary-700`;
    }
    return `${baseClass} bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600`;
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 dark:text-red-400';
      case 'high':
        return 'text-orange-600 dark:text-orange-400';
      case 'medium':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'low':
        return 'text-blue-600 dark:text-blue-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'high':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      {/* Results Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Analysis Results</h2>
            <div className="mt-2 space-y-1">
              <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                <svg className="w-4 h-4 mr-2 text-blue-500 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                {results.insights.length} insights found
              </div>
              <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                <svg className="w-4 h-4 mr-2 text-green-500 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {results.recommendations.length} recommendations
              </div>
            </div>
          </div>

          {/* Controls */}
          <div className="flex flex-col space-y-3">
            {/* Filter Controls */}
            <div className="flex space-x-2">
              <button
                onClick={() => setFilterSeverity('all')}
                className={getFilterButtonClass('all')}
              >
                All ({results.insights.length})
              </button>
              <button
                onClick={() => setFilterSeverity('high')}
                className={getFilterButtonClass('high')}
              >
                High+ ({results.insights.filter(i => i.severity === 'high' || i.severity === 'critical').length})
              </button>
              <button
                onClick={() => setFilterSeverity('critical')}
                className={getFilterButtonClass('critical')}
              >
                Critical ({results.insights.filter(i => i.severity === 'critical').length})
              </button>
            </div>

            {/* Expand/Collapse Controls */}
            <div className="flex space-x-2">
              <button
                onClick={expandAll}
                className="px-3 py-1 text-xs text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
              >
                Expand All
              </button>
              <button
                onClick={collapseAll}
                className="px-3 py-1 text-xs text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
              >
                Collapse All
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-2">Summary</h3>
        <p className="text-base leading-relaxed text-gray-700 dark:text-gray-300">{results.summary}</p>
      </div>

      {/* Insights List */}
      <div className="p-6">
        {filteredInsights.length === 0 ? (
          <div className="text-center py-8">
            <svg className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-gray-500 dark:text-gray-400">
              {filterSeverity === 'all'
                ? 'No insights to display'
                : filterSeverity === 'high'
                ? 'No high or critical severity insights found'
                : 'No critical severity insights found'
              }
            </p>
            {filterSeverity !== 'all' && (
              <button
                onClick={() => setFilterSeverity('all')}
                className="mt-2 text-primary-600 dark:text-primary-400 hover:text-primary-500 dark:hover:text-primary-300 text-sm underline"
              >
                Show all insights
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {filteredInsights.map((insight, index) => (
              <div
                key={index}
                className="bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600"
              >
                <div
                  className="px-4 py-3 cursor-pointer"
                  onClick={() => toggleCard(index)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3">
                      <div className={`flex-shrink-0 ${getSeverityColor(insight.severity)}`}>
                        {getSeverityIcon(insight.severity)}
                      </div>
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                          {insight.title}
                        </h4>
                        <div className="flex items-center space-x-4 mt-1">
                          <span className={`text-xs font-medium uppercase ${getSeverityColor(insight.severity)}`}>
                            {insight.severity}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {insight.category}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {Math.round(insight.confidence * 100)}% confidence
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex-shrink-0">
                      <svg
                        className={`w-4 h-4 text-gray-400 transform transition-transform ${
                          expandedCards.has(index) ? 'rotate-180' : ''
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </div>

                {expandedCards.has(index) && (
                  <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-600">
                    <div className="pt-3">
                      <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
                        {insight.description}
                      </p>

                      {insight.suggestions.length > 0 && (
                        <div>
                          <h5 className="text-xs font-medium text-gray-900 dark:text-white mb-2 uppercase tracking-wide">
                            Suggestions
                          </h5>
                          <ul className="space-y-1">
                            {insight.suggestions.map((suggestion, suggestionIndex) => (
                              <li key={suggestionIndex} className="text-sm text-gray-600 dark:text-gray-300 flex items-start">
                                <span className="text-primary-500 mr-2 flex-shrink-0">•</span>
                                {suggestion}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recommendations */}
      {results.recommendations.length > 0 && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Recommendations</h3>
          <ul className="space-y-2">
            {results.recommendations.map((recommendation, index) => (
              <li key={index} className="text-sm text-gray-600 dark:text-gray-300 flex items-start">
                <span className="text-green-500 mr-2 flex-shrink-0">✓</span>
                {recommendation}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Footer */}
      {filteredInsights.length > 0 && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <div className="flex justify-between items-center text-sm text-gray-600 dark:text-gray-400">
            <span>
              Showing {filteredInsights.length} of {results.insights.length} insights
            </span>
            <span>
              Analysis powered by AI
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultsDisplay;
