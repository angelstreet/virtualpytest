import { Box, CircularProgress, Typography } from '@mui/material';
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Simple Documentation Viewer - Renders markdown files from /docs
 */
const Documentation: React.FC = () => {
  const { section = 'README', subsection, category, page = 'README' } = useParams<{ 
    section?: string; 
    subsection?: string; 
    category?: string;
    page?: string 
  }>();
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
        // /docs/technical/ai/builder -> /docs/technical/ai/builder.md
        // /docs/technical/architecture/components/backend-server -> /docs/technical/architecture/components/backend-server.md
        let mdPath: string;
        if (category && page !== 'README') {
          // 4-level nested path: /docs/technical/architecture/components/backend-server
          mdPath = `/${section}/${subsection}/${category}/${page}.md`;
        } else if (category) {
          // 4-level README: /docs/technical/architecture/components
          mdPath = `/${section}/${subsection}/${category}/README.md`;
        } else if (subsection && page !== 'README') {
          // 3-level nested path: /docs/technical/ai/builder
          mdPath = `/${section}/${subsection}/${page}.md`;
        } else if (subsection) {
          // Subsection README: /docs/technical/ai
          mdPath = `/${section}/${subsection}/README.md`;
        } else if (page === 'README') {
          // Section README: /docs/get-started
          mdPath = `/${section}/README.md`;
        } else {
          // Page in section: /docs/features/unified-controller
          mdPath = `/${section}/${page}.md`;
        }
        
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
  }, [section, subsection, category, page]);

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
        <Box sx={{ p: 3, bgcolor: 'error.dark', borderRadius: 1, border: 1, borderColor: 'error.main' }}>
          <Typography variant="h6" color="error.light">
            Error Loading Documentation
          </Typography>
          <Typography variant="body2" sx={{ mt: 1, color: 'error.light' }}>
            {error}
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4, width: '100%', maxWidth: '1200px', mx: 'auto', minHeight: '80vh' }}>
      <Box 
        sx={{ 
          p: 4, 
          minHeight: '70vh', 
          width: '100%',
          backgroundColor: 'background.paper',
          borderRadius: 2,
          border: 1,
          borderColor: 'divider',
        }}
      >
        <Box sx={{ width: '100%', maxWidth: '900px', mx: 'auto' }}>
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
                  <Box
                    component="code"
                    sx={{
                      backgroundColor: 'action.hover',
                      px: 0.75,
                      py: 0.25,
                      borderRadius: 0.5,
                      fontFamily: 'monospace',
                      fontSize: '0.9em',
                    }}
                    {...props}
                  >
                    {children}
                  </Box>
                );
              }
              return (
                <Box
                  component="pre"
                  sx={{
                    backgroundColor: 'action.hover',
                    p: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    my: 2,
                    border: 1,
                    borderColor: 'divider',
                  }}
                >
                  <code style={{ fontFamily: 'monospace', fontSize: '0.9em' }} {...props}>
                    {children}
                  </code>
                </Box>
              );
            },
            // Style links
            a: ({ children, href }) => {
              // Transform markdown links to React routes
              let transformedHref = href;
              if (href && !href.startsWith('http') && !href.startsWith('#')) {
                // Handle relative paths in markdown
                if (href.startsWith('../')) {
                  // ../features/unified-controller.md -> /docs/features/unified-controller
                  // ../../get-started/quickstart.md -> /docs/get-started/quickstart
                  transformedHref = '/docs/' + href.replace(/^\.\.\/+/g, '').replace(/\.md$/, '').replace(/\/README$/i, '');
                } else if (href.startsWith('./')) {
                  // ./quickstart.md -> current section + quickstart
                  // For nested docs, preserve current path
                  const currentPath = window.location.pathname.replace(/\/docs\/?/, '').replace(/\/$/, '');
                  const parentPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || currentPath;
                  const cleanHref = href.substring(2).replace(/\.md$/, '').replace(/\/README$/i, '');
                  transformedHref = `/docs/${parentPath}/${cleanHref}`.replace(/\/+/g, '/');
                } else {
                  // Direct path
                  transformedHref = href.replace(/\.md$/, '').replace(/\/README$/i, '');
                }
              }
              
              return (
                <Box
                  component="a"
                  href={transformedHref}
                  sx={{
                    color: 'primary.main',
                    textDecoration: 'none',
                    '&:hover': { textDecoration: 'underline' },
                  }}
                  target={href?.startsWith('http') ? '_blank' : undefined}
                  rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
                >
                  {children}
                </Box>
              );
            },
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
                  borderLeft: '4px solid',
                  borderColor: 'primary.main',
                  pl: 2,
                  py: 0.5,
                  my: 2,
                  backgroundColor: 'action.hover',
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
                  border: 1,
                  borderColor: 'divider',
                  p: 1.5,
                  backgroundColor: 'action.hover',
                  fontWeight: 600,
                  textAlign: 'left',
                }}
              >
                {children}
              </Box>
            ),
            td: ({ children }) => (
              <Box component="td" sx={{ border: 1, borderColor: 'divider', p: 1.5 }}>
                {children}
              </Box>
            ),
            // Style horizontal rules
            hr: () => <Box component="hr" sx={{ my: 3, border: 'none', borderTop: 1, borderColor: 'divider' }} />,
          }}
        >
          {markdown}
        </ReactMarkdown>
        </Box>
      </Box>
    </Box>
  );
};

export default Documentation;

