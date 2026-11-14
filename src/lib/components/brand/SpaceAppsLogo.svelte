<script lang="ts">
	/**
	 * Official NASA Space Apps Challenge 2026 logos, white colourway for dark backgrounds,
	 * from the official logo package (static/brand/logo). The brand guide forbids redrawing or
	 * altering the logo, so these are the supplied files used as-is.
	 * - 'default': horizontal lockup (preferred)
	 * - 'motif': self-contained orbit with the event name
	 * - 'small': orbit mark only, for space-limited spots (decorative next to a text label)
	 */
	let {
		variant = 'small',
		class: className = 'h-8 w-8'
	}: {
		variant?: 'small' | 'default' | 'motif';
		class?: string;
	} = $props();

	const files = {
		default: '/brand/logo/space-apps-logo.svg',
		motif: '/brand/logo/space-apps-motif.svg',
		small: '/brand/logo/space-apps-small.svg'
	};
</script>

<img
	src={files[variant]}
	alt={variant === 'small' ? '' : 'NASA Space Apps Challenge'}
	class="{className} object-contain"
	draggable="false"
/>
