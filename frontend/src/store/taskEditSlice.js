import { createSlice } from '@reduxjs/toolkit';

const taskEditSlice = createSlice({
    name: 'taskEdit',
    initialState: {
        editingTask: null,
        editRequest: null,
        changes: null
    },
    reducers: {
        setEditingTask: (state, action) => {
            state.editingTask = action.payload;
        },
        setEditRequest: (state, action) => {
            state.editRequest = action.payload;
        },
        setChanges: (state, action) => {
            state.changes = action.payload;
        }
    }
});

export const { setEditingTask, setEditRequest, setChanges } = taskEditSlice.actions;
export default taskEditSlice.reducer; 