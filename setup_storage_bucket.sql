-- Setup script for Supabase Storage
-- Run this in your Supabase SQL Editor

-- 1. Create the generated-images bucket (if not exists)
-- Note: You should create this via the Supabase Dashboard UI first
-- Dashboard → Storage → New Bucket → Name: "generated-images" → Public: Yes

-- 2. Set up storage policies for the generated-images bucket

-- Allow service role to upload images
CREATE POLICY IF NOT EXISTS "Allow service role uploads to generated-images"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'generated-images');

-- Allow authenticated users to upload images
CREATE POLICY IF NOT EXISTS "Allow authenticated uploads to generated-images"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'generated-images');

-- Allow public to upload images (for anonymous users)
CREATE POLICY IF NOT EXISTS "Allow public uploads to generated-images"
ON storage.objects FOR INSERT
TO public
WITH CHECK (bucket_id = 'generated-images');

-- Allow public to read/download images
CREATE POLICY IF NOT EXISTS "Allow public reads from generated-images"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'generated-images');

-- Allow users to delete their own images (optional)
CREATE POLICY IF NOT EXISTS "Allow users to delete own images"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'generated-images' AND auth.uid()::text = (storage.foldername(name))[1]);

-- 3. Verify the policies were created
SELECT 
    policyname,
    cmd,
    roles
FROM pg_policies 
WHERE schemaname = 'storage' 
AND tablename = 'objects'
AND policyname LIKE '%generated-images%';
