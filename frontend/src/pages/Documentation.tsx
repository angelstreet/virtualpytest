import { Box, CircularProgress, Paper, Typography } from '@mui/material';
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Simple Documentation Viewer - Renders markdown files from /docs
 */
const Documentation: React.FC = () => {
  const { section = 'README', page = 'README' } = useParams<{ section?: string; page?: string }>();
  const [markdown, setMarkdown] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchMarkdown = async () => {
      setLoading(true);
      setError('');

      try {
        // Construct path to markdown file
        // Examples:
        // /docs/get-started -> /docs/get-started/README.md
        // /docs/features/unified-controller -> /docs/features/unified-controller.md
        const mdPath = page === 'README' ? `/${section}/README.md` : `/${section}/${page}.md`;
        const fullPath = `/docs${mdPath}`;

        const response = await fetch(fullPath);

        if (!response.ok) {
          throw new Error(`Documentation not found: ${fullPath}`);
        }

        const text = await response.text();
        setMarkdown(text);
      } catch (err) {
        console.error('Error loading documentation:', err);
        setError(err instanceof Error ? err.message : 'Failed to load documentation');
      } finally {
        setLoading(false);
      }
    };

    fetchMarkdown();
  }, [section, page]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 4 }}>
        <Paper sx={{ p: 3, bgcolor: 'error.light' }}>
          <Typography variant="h6" color="error">
            Error Loading Documentation
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            {error}
          </Typography>
        </Paper>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4, maxWidth: '1200px', mx: 'auto' }}>
      <Paper sx={{ p: 4 }}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            // Style headers
            h1: ({ children }) => (
              <Typography variant="h3" component="h1" gutterBottom sx={{ mt: 2, mb: 2, fontWeight: 600 }}>
                {children}
              </Typography>
            ),
            h2: ({ children }) => (
              <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 3, mb: 2, fontWeight: 600 }}>
                {children}
              </Typography>
            ),
            h3: ({ children }) => (
              <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 2, mb: 1.5, fontWeight: 600 }}>
                {children}
              </Typography>
            ),
            h4: ({ children }) => (
              <Typography variant="h6" component="h4" gutterBottom sx={{ mt: 2, mb: 1, fontWeight: 600 }}>
                {children}
              </Typography>
            ),
            // Style paragraphs
            p: ({ children }) => (
              <Typography variant="body1" paragraph sx={{ lineHeight: 1.7 }}>
                {children}
              </Typography>
            ),
            // Style code blocks
            code: ({ inline, children, ...props }: any) => {
              if (inline) {
                return (
                  <code
                    style={{
                      backgroundColor: '#f5f5f5',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontFamily: 'monospace',
                      fontSize: '0.9em',
                    }}
                    {...props}
                  >
                    {children}
                  </code>
                );
              }
              return (
                <Box
                  component="pre"
                  sx={{
                    backgroundColor: '#f5f5f5',
                    p: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    my: 2,
                  }}
                >
                  <code style={{ fontFamily: 'monospace', fontSize: '0.9em' }} {...props}>
                    {children}
                  </code>
                </Box>
              );
            },
            // Style links
            a: ({ children, href }) => (
              <a
                href={href}
                style={{ color: '#1976d2', textDecoration: 'none' }}
                target={href?.startsWith('http') ? '_blank' : undefined}
                rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
              >
                {children}
              </a>
            ),
            // Style lists
            ul: ({ children }) => (
              <Box component="ul" sx={{ pl: 3, my: 1.5 }}>
                {children}
              </Box>
            ),
            ol: ({ children }) => (
              <Box component="ol" sx={{ pl: 3, my: 1.5 }}>
                {children}
              </Box>
            ),
            li: ({ children }) => (
              <Typography component="li" variant="body1" sx={{ mb: 0.5, lineHeight: 1.7 }}>
                {children}
              </Typography>
            ),
            // Style blockquotes
            blockquote: ({ children }) => (
              <Box
                sx={{
                  borderLeft: '4px solid #1976d2',
                  pl: 2,
                  py: 0.5,
                  my: 2,
                  backgroundColor: '#f5f5f5',
                }}
              >
                {children}
              </Box>
            ),
            // Style tables
            table: ({ children }) => (
              <Box sx={{ overflowX: 'auto', my: 2 }}>
                <Box component="table" sx={{ width: '100%', borderCollapse: 'collapse' }}>
                  {children}
                </Box>
              </Box>
            ),
            th: ({ children }) => (
              <Box
                component="th"
                sx={{
                  border: '1px solid #ddd',
                  p: 1.5,
                  backgroundColor: '#f5f5f5',
                  fontWeight: 600,
                  textAlign: 'left',
                }}
              >
                {children}
              </Box>
            ),
            td: ({ children }) => (
              <Box component="td" sx={{ border: '1px solid #ddd', p: 1.5 }}>
                {children}
              </Box>
            ),
            // Style horizontal rules
            hr: () => <Box component="hr" sx={{ my: 3, border: 'none', borderTop: '1px solid #ddd' }} />,
          }}
        >
          {markdown}
        </ReactMarkdown>
      </Paper>
    </Box>
  );
};

export default Documentation;

