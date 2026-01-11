import React from 'react';
import Logger from '../services/Logger';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(_error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        Logger.error(
            error.message || "React Error Boundary Caught Error",
            "ErrorBoundary",
            error.stack,
            { componentStack: errorInfo.componentStack }
        );
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="h-screen w-full flex flex-col items-center justify-center bg-slate-50 text-slate-800 p-8 text-center">
                    <h1 className="text-4xl font-black mb-4">Something went wrong.</h1>
                    <p className="text-lg text-slate-600 mb-8 max-w-md">
                        Our autonomous agents have been notified and are already analyzing the issue.
                    </p>
                    <button
                        onClick={() => window.location.reload()}
                        className="bg-indigo-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-indigo-700 transition-all"
                    >
                        Reload Application
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
