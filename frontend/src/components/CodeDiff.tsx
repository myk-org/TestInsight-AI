import React, { useMemo } from 'react';

interface CodeDiffProps {
  content: string;
}

interface DiffLine {
  type: 'context' | 'addition' | 'deletion' | 'header' | 'location';
  content: string;
  lineNumber?: {
    old?: number;
    new?: number;
  };
}

const CodeDiff: React.FC<CodeDiffProps> = ({ content }) => {
  const parsedDiff = useMemo(() => {
    const lines = content.split('\n');
    const diffLines: DiffLine[] = [];
    let oldLineNumber = 0;
    let newLineNumber = 0;

    for (const line of lines) {
      if (line.startsWith('```')) {
        // Skip markdown code block markers
        continue;
      } else if (line.startsWith('+++') || line.startsWith('---')) {
        // File headers
        diffLines.push({
          type: 'header',
          content: line,
        });
      } else if (line.startsWith('@@')) {
        // Location headers
        const match = line.match(/@@\s*-(\d+)(?:,\d+)?\s*\+(\d+)(?:,\d+)?\s*@@/);
        if (match) {
          oldLineNumber = parseInt(match[1]) - 1;
          newLineNumber = parseInt(match[2]) - 1;
        }
        diffLines.push({
          type: 'location',
          content: line,
        });
      } else if (line.startsWith('+')) {
        // Addition
        newLineNumber++;
        diffLines.push({
          type: 'addition',
          content: line.substring(1),
          lineNumber: { new: newLineNumber },
        });
      } else if (line.startsWith('-')) {
        // Deletion
        oldLineNumber++;
        diffLines.push({
          type: 'deletion',
          content: line.substring(1),
          lineNumber: { old: oldLineNumber },
        });
      } else if (line.startsWith(' ') || (!line.startsWith('+') && !line.startsWith('-') && !line.startsWith('@'))) {
        // Context line
        oldLineNumber++;
        newLineNumber++;
        diffLines.push({
          type: 'context',
          content: line.startsWith(' ') ? line.substring(1) : line,
          lineNumber: { old: oldLineNumber, new: newLineNumber },
        });
      }
    }

    return diffLines;
  }, [content]);

  const getLineClassName = (type: DiffLine['type']) => {
    switch (type) {
      case 'addition':
        return 'bg-green-50 border-l-4 border-green-400 text-green-900';
      case 'deletion':
        return 'bg-red-50 border-l-4 border-red-400 text-red-900';
      case 'context':
        return 'bg-white border-l-4 border-gray-200 text-gray-700';
      case 'header':
        return 'bg-gray-100 border-l-4 border-gray-400 text-gray-800 font-semibold';
      case 'location':
        return 'bg-blue-50 border-l-4 border-blue-400 text-blue-800 font-medium';
      default:
        return 'bg-white text-gray-700';
    }
  };

  const getLineIcon = (type: DiffLine['type']) => {
    switch (type) {
      case 'addition':
        return (
          <span className="inline-flex items-center justify-center w-4 h-4 text-green-600 font-bold">
            +
          </span>
        );
      case 'deletion':
        return (
          <span className="inline-flex items-center justify-center w-4 h-4 text-red-600 font-bold">
            −
          </span>
        );
      case 'context':
        return (
          <span className="inline-flex items-center justify-center w-4 h-4 text-gray-400">
            ⋅
          </span>
        );
      default:
        return null;
    }
  };

  // If content doesn't look like a diff, render as plain code
  if (!content.includes('+++') && !content.includes('---') && !content.includes('@@')) {
    // Check if it's markdown code block
    const codeBlockMatch = content.match(/```(\w+)?\n?([\s\S]*?)```/);
    if (codeBlockMatch) {
      const code = codeBlockMatch[2];
      return (
        <div className="bg-gray-900 dark:bg-gray-800 rounded-lg overflow-hidden">
          <div className="px-4 py-2 bg-gray-800 dark:bg-gray-700 text-gray-300 dark:text-gray-200 text-xs font-medium border-b border-gray-700 dark:border-gray-600">
            Code Suggestion
          </div>
          <div className="p-4">
            <pre className="text-sm text-gray-100">
              <code>{code}</code>
            </pre>
          </div>
        </div>
      );
    }

    // Plain text with some formatting
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-2 bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs font-medium border-b border-gray-200 dark:border-gray-600">
          Suggested Changes
        </div>
        <div className="p-4">
          <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
            {content}
          </pre>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <div className="px-4 py-2 bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs font-medium border-b border-gray-200 dark:border-gray-600 flex items-center">
        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
        Diff View
      </div>
      <div className="max-h-96 overflow-auto">
        {parsedDiff.map((line, index) => (
          <div
            key={index}
            className={`flex ${getLineClassName(line.type)}`}
          >
            {/* Line Numbers */}
            <div className="flex-shrink-0 w-16 px-2 py-1 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 border-r border-gray-200 dark:border-gray-600 select-none">
              <div className="flex">
                <span className="w-6 text-right">
                  {line.lineNumber?.old || ''}
                </span>
                <span className="w-6 text-right ml-1">
                  {line.lineNumber?.new || ''}
                </span>
              </div>
            </div>

            {/* Line Indicator */}
            <div className="flex-shrink-0 w-6 px-1 py-1 text-center">
              {getLineIcon(line.type)}
            </div>

            {/* Line Content */}
            <div className="flex-1 px-2 py-1 min-w-0">
              <code className="text-sm font-mono whitespace-pre-wrap break-words">
                {line.content || '\u00A0'} {/* Non-breaking space for empty lines */}
              </code>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CodeDiff;
