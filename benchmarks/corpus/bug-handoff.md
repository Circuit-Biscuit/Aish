The login form submits twice when the user presses Enter. The submit handler in
src/ui/LoginForm.tsx is bound to both the form onSubmit event and the button
onClick event, so pressing Enter triggers both paths. I reproduced this in
Chrome and Firefox. It does not happen when clicking the button directly.
The fix is to remove the onClick binding and keep only onSubmit.
