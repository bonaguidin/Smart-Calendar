import React, { useState, useEffect } from 'react';
import { useSpring, animated } from 'react-spring';
import { useCalendar } from '../context/CalendarContext';
import { useDispatch, useSelector } from 'react-redux';
import { FaArrowLeft, FaArrowRight, FaClock, FaPencilAlt } from 'react-icons/fa';
import '../styles/AITaskEditor.css';

const AITaskEditor = ({ task, editRequest, onClose }) => {
    const dispatch = useDispatch();
    const { updateTask } = useCalendar();
    const [changes, setChanges] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedChanges, setSelectedChanges] = useState(new Set());

    // Animation for diff view
    const diffAnimation = useSpring({
        from: { opacity: 0, transform: 'translateY(20px)' },
        to: { opacity: 1, transform: 'translateY(0)' },
        config: { tension: 300, friction: 20 }
    });

    useEffect(() => {
        const fetchChanges = async () => {
            try {
                const response = await fetch('http://localhost:5000/api/parse-edit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        task,
                        edit_request: editRequest
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to parse edit request');
                }

                const data = await response.json();
                setChanges(data);
                setLoading(false);
            } catch (err) {
                setError(err.message);
                setLoading(false);
            }
        };

        fetchChanges();
    }, [task, editRequest]);

    const getChangeIcon = (changeType) => {
        switch (changeType) {
            case 'date_shift':
                return <FaArrowRight className="change-icon" />;
            case 'time_change':
                return <FaClock className="change-icon" />;
            case 'content_change':
                return <FaPencilAlt className="change-icon" />;
            default:
                return null;
        }
    };

    const renderDiff = (original, modified, type) => {
        return (
            <animated.div style={diffAnimation} className="diff-container">
                <div className="diff-row">
                    <div className="diff-original">
                        {getChangeIcon(type)}
                        <span className="diff-label">Original:</span>
                        <span className="diff-value">{original}</span>
                    </div>
                    <div className="diff-modified">
                        <span className="diff-label">Modified:</span>
                        <span className="diff-value">{modified}</span>
                    </div>
                </div>
            </animated.div>
        );
    };

    const handleChangeSelection = (changeId) => {
        setSelectedChanges(prev => {
            const newSet = new Set(prev);
            if (newSet.has(changeId)) {
                newSet.delete(changeId);
            } else {
                newSet.add(changeId);
            }
            return newSet;
        });
    };

    const handleApplyChanges = async () => {
        try {
            const selectedChangesList = Array.from(selectedChanges);
            const modifiedTask = { ...task };

            // Apply selected changes
            selectedChangesList.forEach(changeId => {
                const change = changes.changes[changeId];
                Object.assign(modifiedTask, change);
            });

            // Update task in calendar
            await updateTask(modifiedTask);
            onClose();
        } catch (err) {
            setError(err.message);
        }
    };

    if (loading) {
        return <div className="ai-editor-loading">Analyzing changes...</div>;
    }

    if (error) {
        return <div className="ai-editor-error">Error: {error}</div>;
    }

    return (
        <div className="ai-task-editor">
            <h3>Suggested Changes</h3>
            
            <div className="changes-container">
                {changes && Object.entries(changes.changes).map(([id, change]) => (
                    <div key={id} className="change-item">
                        <label className="change-checkbox">
                            <input
                                type="checkbox"
                                checked={selectedChanges.has(id)}
                                onChange={() => handleChangeSelection(id)}
                            />
                            <span className="checkbox-label">Apply this change</span>
                        </label>
                        
                        {change.type === 'date_shift' && renderDiff(
                            task.start_date,
                            change.start_date,
                            'date_shift'
                        )}
                        
                        {change.type === 'time_change' && renderDiff(
                            task.time,
                            change.time,
                            'time_change'
                        )}
                        
                        {change.type === 'content_change' && renderDiff(
                            task.title,
                            change.title,
                            'content_change'
                        )}
                    </div>
                ))}
            </div>

            <div className="editor-actions">
                <button 
                    className="apply-button"
                    onClick={handleApplyChanges}
                    disabled={selectedChanges.size === 0}
                >
                    Apply Selected Changes
                </button>
                <button 
                    className="cancel-button"
                    onClick={onClose}
                >
                    Cancel
                </button>
            </div>
        </div>
    );
};

export default AITaskEditor; 